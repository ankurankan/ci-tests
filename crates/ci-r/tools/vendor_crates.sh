#!/usr/bin/env bash
# Regenerate src/rust/vendor.tar.xz for the R package.
#
# Crates that none of the supported platforms build (windows-sys, walkdir, ...)
# are replaced by empty stubs so the bundle stays small enough for CRAN's 5 MB
# source-package limit while Cargo.lock still resolves offline.
#
# cargo vendor-filterer keeps only the crates needed on *every* platform it is
# given, so it is run once per platform and the results are merged: a crate is
# real in the bundle if any supported platform needs it.
#
# Requires: cargo install cargo-vendor-filterer --locked
set -euo pipefail

PLATFORMS=(
    x86_64-unknown-linux-gnu
    aarch64-unknown-linux-gnu
    x86_64-apple-darwin
    aarch64-apple-darwin
    x86_64-pc-windows-gnu
)
EMPTY_SHA256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855

cd "$(dirname "$0")/../src/rust"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

# A stub's src/lib.rs is empty, which its checksum file records.
is_stub() {
    grep -q "\"src/lib.rs\":\"$EMPTY_SHA256\"" "$1/.cargo-checksum.json"
}

for platform in "${PLATFORMS[@]}"; do
    cargo vendor-filterer --platform="$platform" --keep-dep-kinds=no-dev \
        "$work/$platform" >/dev/null 2>&1
done

merged="$work/vendor"
cp -a "$work/${PLATFORMS[0]}" "$merged"
for platform in "${PLATFORMS[@]:1}"; do
    for crate in "$work/$platform"/*/; do
        name="$(basename "$crate")"
        if is_stub "$merged/$name" && ! is_stub "$crate"; then
            rm -rf "${merged:?}/$name"
            cp -a "$crate" "$merged/$name"
        fi
    done
done

echo "Stubbed crates:"
for crate in "$merged"/*/; do
    if is_stub "$crate"; then basename "$crate"; fi
done | sort | sed 's/^/  /'

rm -rf vendor
cp -a "$merged" vendor
tar cJf vendor.tar.xz vendor
rm -rf vendor
