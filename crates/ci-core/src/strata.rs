//! Conditioning-set row grouping and its dataset-owned, budget-bounded cache.

use std::collections::HashMap;
use std::sync::{Arc, RwLock};

use crate::dataset::Dataset;
use crate::error::CiError;

/// Total byte budget for cached stratum partitions (see
/// [`Dataset::strata_partition`]): partitions are cached until the budget is
/// reached; further conditioning sets compute on the fly without caching
/// (monotone — no eviction).
const MAX_STRATA_CACHE_BYTES: usize = 256 << 20;

/// Keyed cache of stratum partitions plus its current byte footprint.
#[derive(Debug, Default)]
struct StrataCacheInner {
    map: HashMap<Vec<usize>, Arc<StrataPartition>>,
    bytes: usize,
}

impl StrataCacheInner {
    /// Insert `partition` under `key` iff it fits in `budget`; returns whether
    /// it was cached. Factored out so tests can drive a tiny budget.
    ///
    /// The caller must ensure `key` is absent (the cache's double-checked
    /// lookup guarantees this); inserting an existing key would double-count
    /// `bytes`.
    fn insert_within_budget(
        &mut self,
        key: Vec<usize>,
        partition: &Arc<StrataPartition>,
        budget: usize,
    ) -> bool {
        debug_assert!(
            !self.map.contains_key(&key),
            "insert_within_budget requires an absent key"
        );
        let size = partition.approx_bytes();
        if self.bytes + size > budget {
            return false;
        }
        self.bytes += size;
        self.map.insert(key, Arc::clone(partition));
        true
    }
}

/// Lazily caches partitions by sorted conditioning-set indices.
#[derive(Debug, Default)]
pub(crate) struct StrataCache {
    inner: RwLock<StrataCacheInner>,
}

impl StrataCache {
    /// Build outside the lock, then cache within the monotone byte budget.
    pub(crate) fn get_or_build(
        &self,
        data: &Dataset,
        z: &[usize],
    ) -> Result<Arc<StrataPartition>, CiError> {
        let mut key: Vec<usize> = z.to_vec();
        key.sort_unstable();

        if let Some(hit) = self
            .inner
            .read()
            .expect("strata cache lock poisoned")
            .map
            .get(&key)
        {
            return Ok(Arc::clone(hit));
        }

        // Build outside the lock; gather columns in sorted order so equal sets
        // yield byte-identical partitions.
        let z_columns: Vec<(&[usize], usize)> = key
            .iter()
            .map(|&zi| data.discrete(zi))
            .collect::<Result<_, _>>()?;
        let partition = Arc::new(build_strata_partition(&z_columns, data.n_rows()));

        let mut cache = self.inner.write().expect("strata cache lock poisoned");
        if let Some(hit) = cache.map.get(&key) {
            return Ok(Arc::clone(hit)); // another thread won the race
        }
        cache.insert_within_budget(key, &partition, MAX_STRATA_CACHE_BYTES);
        Ok(partition)
    }
}

/// Rows grouped by the observed combinations of a conditioning set `Z`:
/// `rows[starts[s] .. starts[s + 1]]` are the row indices of stratum `s`
/// (original row order within each stratum). Built once per distinct `Z` and
/// cached on the [`crate::dataset::Dataset`].
#[derive(Debug)]
pub(crate) struct StrataPartition {
    pub(crate) starts: Vec<u32>,
    pub(crate) rows: Vec<u32>,
}

impl StrataPartition {
    /// Number of observed strata.
    pub(crate) fn n_strata(&self) -> usize {
        self.starts.len().saturating_sub(1)
    }

    /// Approximate heap size, for the cache budget.
    fn approx_bytes(&self) -> usize {
        4 * (self.starts.len() + self.rows.len())
    }
}

/// When the folded space (`∏ k_zi`) fits within this many times the row count
/// plus slack, use a flat `u32::MAX`-sentinel remap array instead of a `HashMap`.
const DENSE_REMAP_SLACK: usize = 4096;

/// Mixed-radix strides over the Z cardinalities, and the total `∏ k_zi`.
/// `None` if the product overflows `usize` (caller falls back to hashing).
fn fold_strides(z_columns: &[(&[usize], usize)]) -> Option<(Vec<usize>, usize)> {
    let mut strides = Vec::with_capacity(z_columns.len());
    let mut acc: usize = 1;
    for &(_, card) in z_columns {
        strides.push(acc);
        // card >= 1 whenever there are rows; max(1) keeps n == 0 safe.
        acc = acc.checked_mul(card.max(1))?;
    }
    Some((strides, acc))
}

/// Map each key to a first-seen dense id in `[0, n_strata)`, pushing the ids
/// onto `dense_ids`; returns the number of distinct keys (`n_strata`).
fn densify_hashed<K: Eq + std::hash::Hash>(
    keys: impl IntoIterator<Item = K>,
    dense_ids: &mut Vec<u32>,
) -> usize {
    let mut remap: std::collections::HashMap<K, u32> = std::collections::HashMap::new();
    for key in keys {
        let next = u32::try_from(remap.len()).expect("strata bounded by row count");
        dense_ids.push(*remap.entry(key).or_insert(next));
    }
    remap.len()
}

/// Group rows by the combination of the `Z` columns' codes. Strata are
/// identified by a mixed-radix fold (no per-row allocation); if `∏ k_zi`
/// overflows `usize` (only reachable with very many / very-high-cardinality Z
/// columns), falls back to hashing the per-row code tuple. Rows are then
/// grouped with a counting sort.
pub(crate) fn build_strata_partition(z_columns: &[(&[usize], usize)], n: usize) -> StrataPartition {
    let mut dense_ids: Vec<u32> = Vec::with_capacity(n);
    let n_strata: usize;

    if let Some((strides, total)) = fold_strides(z_columns) {
        // Pass 1: folded stratum id per row.
        let folded: Vec<usize> = (0..n)
            .map(|row| {
                z_columns
                    .iter()
                    .zip(&strides)
                    .map(|((codes, _), stride)| codes[row] * stride)
                    .sum()
            })
            .collect();
        // Pass 2: densify (flat remap when the folded space is small).
        if total <= 4 * n + DENSE_REMAP_SLACK {
            let mut remap = vec![u32::MAX; total];
            let mut next = 0u32;
            for &f in &folded {
                if remap[f] == u32::MAX {
                    remap[f] = next;
                    next += 1;
                }
                dense_ids.push(remap[f]);
            }
            n_strata = next as usize;
        } else {
            n_strata = densify_hashed(folded.iter().copied(), &mut dense_ids);
        }
    } else {
        // Radix overflow: hash the per-row code tuple to first-seen dense ids.
        let keys = (0..n).map(|row| {
            z_columns
                .iter()
                .map(|(codes, _)| codes[row])
                .collect::<Vec<usize>>()
        });
        n_strata = densify_hashed(keys, &mut dense_ids);
    }

    // Pass 3: counting-sort row indices by dense stratum id.
    let mut starts = vec![0u32; n_strata + 1];
    for &d in &dense_ids {
        starts[d as usize + 1] += 1;
    }
    for s in 0..n_strata {
        starts[s + 1] += starts[s];
    }
    let mut cursor = starts.clone();
    let mut rows = vec![0u32; n];
    for (row, &d) in dense_ids.iter().enumerate() {
        let slot = cursor[d as usize] as usize;
        rows[slot] = u32::try_from(row).expect("row count fits in u32");
        cursor[d as usize] += 1;
    }

    StrataPartition { starts, rows }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::dataset::ColumnKind;

    #[test]
    fn strata_partition_is_cached_and_order_insensitive() {
        let ds = Dataset::from_columns(vec![
            (
                "x".into(),
                ColumnKind::Discrete,
                vec![1., 2., 1., 2., 1., 2.],
            ),
            (
                "z1".into(),
                ColumnKind::Discrete,
                vec![1., 1., 2., 2., 1., 2.],
            ),
            (
                "z2".into(),
                ColumnKind::Discrete,
                vec![2., 1., 2., 1., 1., 2.],
            ),
        ])
        .unwrap();
        let a = ds.strata_partition(&[1, 2]).unwrap();
        let b = ds.strata_partition(&[1, 2]).unwrap();
        let c = ds.strata_partition(&[2, 1]).unwrap();
        assert!(
            std::sync::Arc::ptr_eq(&a, &b),
            "repeat query must hit the cache"
        );
        assert!(std::sync::Arc::ptr_eq(&a, &c), "z order must not matter");
        // A continuous column in z surfaces the usual WrongColumnKind.
        let ds2 = Dataset::from_columns(vec![
            ("x".into(), ColumnKind::Discrete, vec![1., 2.]),
            ("c".into(), ColumnKind::Continuous, vec![0.1, 0.2]),
        ])
        .unwrap();
        assert!(matches!(
            ds2.strata_partition(&[1]),
            Err(CiError::WrongColumnKind(_))
        ));
    }

    #[test]
    fn strata_cache_respects_budget() {
        let p = std::sync::Arc::new(StrataPartition {
            starts: vec![0, 2, 4],
            rows: vec![0, 1, 2, 3],
        });
        let mut inner = StrataCacheInner::default();
        // A zero budget rejects even the first insert (strict `>` boundary).
        assert!(!inner.insert_within_budget(vec![0], &p, 0));
        assert_eq!(inner.bytes, 0);
        // Budget fits exactly one copy (7 u32s = 28 bytes).
        assert!(inner.insert_within_budget(vec![1], &p, 28));
        assert!(!inner.insert_within_budget(vec![2], &p, 28), "over budget");
        assert!(inner.map.contains_key(&vec![1]));
        assert!(!inner.map.contains_key(&vec![2]));
    }
}
