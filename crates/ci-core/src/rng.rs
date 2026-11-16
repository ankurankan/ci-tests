//! Deterministic `SplitMix64` generator for permutation nulls.
//!
//! The stream is fully specified (see the design spec, "Permutation RNG") so
//! that p-values are reproducible across releases and dependency upgrades, and
//! so the Python fixture generator can port it bit-for-bit. No external RNG
//! crate is involved.

/// `SplitMix64` pseudo-random generator with a single `u64` of state.
#[derive(Debug, Clone)]
pub(crate) struct SplitMix64 {
    state: u64,
}

impl SplitMix64 {
    /// Creates a generator whose state starts at `seed`.
    pub(crate) fn new(seed: u64) -> Self {
        Self { state: seed }
    }

    /// Advances the state and returns the next 64-bit output.
    pub(crate) fn next_u64(&mut self) -> u64 {
        self.state = self.state.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.state;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }

    /// Unbiased draw uniform on `[0, m)` by rejection sampling. Requires `m ≥ 1`.
    pub(crate) fn bounded(&mut self, m: u64) -> u64 {
        debug_assert!(m >= 1, "bounded requires m >= 1");
        // t = (2^64 - m) mod m; draws below t are rejected to remove modulo bias.
        let t = m.wrapping_neg() % m;
        loop {
            let r = self.next_u64();
            if r >= t {
                return r % m;
            }
        }
    }
}

/// Fills `out` with the identity permutation `0..n` and shuffles it in place
/// with Fisher–Yates, drawing from `rng`. The generator stream continues across
/// calls, so successive permutations differ.
pub(crate) fn shuffle_identity(rng: &mut SplitMix64, out: &mut [usize]) {
    for (i, slot) in out.iter_mut().enumerate() {
        *slot = i;
    }
    for i in (1..out.len()).rev() {
        let j = usize::try_from(rng.bounded(u64::try_from(i + 1).unwrap())).unwrap();
        out.swap(i, j);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn splitmix64_seed0_reference_stream() {
        let mut r = SplitMix64::new(0);
        assert_eq!(r.next_u64(), 0xE220_A839_7B1D_CDAF);
        assert_eq!(r.next_u64(), 0x6E78_9E6A_A1B9_65F4);
        assert_eq!(r.next_u64(), 0x06C4_5D18_8009_454F);
    }

    #[test]
    fn bounded_stays_in_range_and_handles_one() {
        let mut r = SplitMix64::new(42);
        let mut seen = [false; 7];
        for _ in 0..10_000 {
            let v = r.bounded(7);
            assert!(v < 7);
            seen[usize::try_from(v).unwrap()] = true;
        }
        assert!(seen.iter().all(|&s| s));
        for _ in 0..100 {
            assert_eq!(r.bounded(1), 0);
        }
    }

    #[test]
    fn shuffle_is_a_permutation_and_seed_deterministic() {
        let n = 50;
        let mut a = vec![0usize; n];
        let mut b = vec![0usize; n];
        let mut c = vec![0usize; n];
        shuffle_identity(&mut SplitMix64::new(0), &mut a);
        shuffle_identity(&mut SplitMix64::new(0), &mut b);
        shuffle_identity(&mut SplitMix64::new(1), &mut c);

        let mut sorted = a.clone();
        sorted.sort_unstable();
        assert_eq!(sorted, (0..n).collect::<Vec<_>>());
        assert_eq!(a, b);
        assert_ne!(a, c);
    }

    #[test]
    fn shuffle_seed0_n10_is_pinned() {
        let mut perm = vec![0usize; 10];
        shuffle_identity(&mut SplitMix64::new(0), &mut perm);
        // Mirrored in tests/fixtures/test_generate_golden.py.
        assert_eq!(perm, vec![6, 3, 2, 9, 8, 1, 4, 7, 0, 5]);
    }

    #[test]
    fn shuffle_handles_n_0_and_1() {
        let mut rng = SplitMix64::new(0);
        let mut empty: Vec<usize> = Vec::new();
        shuffle_identity(&mut rng, &mut empty);
        assert!(empty.is_empty());

        let mut one = vec![0usize; 1];
        shuffle_identity(&mut rng, &mut one);
        assert_eq!(one, vec![0]);
    }
}
