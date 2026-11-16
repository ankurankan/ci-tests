from __future__ import annotations

import tarfile
from pathlib import Path

import pytest
import tomllib
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
R_PACKAGE = REPO_ROOT / "crates" / "ci-r"
R_RUST = R_PACKAGE / "src" / "rust"
VENDOR_ARCHIVE = R_RUST / "vendor.tar.xz"
THIRD_PARTY_NOTICE = R_PACKAGE / "THIRD-PARTY-NOTICES"
EXTENDR_CRATES = {"extendr-api", "extendr-ffi", "extendr-macros"}
# Crates unused on every supported R platform; vendored as empty stubs.
PLATFORM_STUBBED_CRATES = {
    "bytemuck_derive",
    "crunchy",
    "gemm-f16",
    "half",
    "hermit-abi",
    "itoa",
    "memchr",
    "same-file",
    "serde",
    "serde_core",
    "serde_derive",
    "serde_json",
    "walkdir",
    "winapi-util",
    "windows-link",
    "windows-sys",
    "zerocopy",
    "zerocopy-derive",
    "zmij",
}


def registry_crates_from_lockfile() -> set[tuple[str, str]]:
    lockfile = tomllib.loads((R_RUST / "Cargo.lock").read_text())
    return {
        (package["name"], package["version"])
        for package in lockfile["package"]
        if package.get("source", "").startswith("registry+")
    }


def vendored_crate_manifests() -> dict[tuple[str, str], dict[str, object]]:
    manifests: dict[tuple[str, str], dict[str, object]] = {}
    with tarfile.open(VENDOR_ARCHIVE, "r:xz") as archive:
        for member in archive.getmembers():
            parts = Path(member.name).parts
            if len(parts) == 3 and parts[0] == "vendor" and parts[-1] == "Cargo.toml":
                handle = archive.extractfile(member)
                assert handle is not None
                manifest = tomllib.loads(handle.read().decode("utf-8"))
                package = manifest["package"]
                manifests[(package["name"], package["version"])] = package
    return manifests


def load_workflow(name: str) -> dict[str, object]:
    return yaml.safe_load((REPO_ROOT / ".github" / "workflows" / name).read_text())


def named_step(workflow: dict[str, object], job: str, name: str) -> dict[str, object]:
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    selected_job = jobs[job]
    assert isinstance(selected_job, dict)
    steps = selected_job["steps"]
    assert isinstance(steps, list)
    return next(
        step for step in steps if isinstance(step, dict) and step.get("name") == name
    )


def test_r_msrv_is_advertised_preflighted_and_exercised() -> None:
    manifest = tomllib.loads(
        (REPO_ROOT / "crates" / "ci-r" / "src" / "rust" / "Cargo.toml").read_text()
    )
    assert manifest["package"]["rust-version"] == "1.85"

    description = (REPO_ROOT / "crates" / "ci-r" / "DESCRIPTION").read_text()
    assert "rustc >= 1.85.0" in description

    workflow = load_workflow("r.yml")
    rust_step = named_step(workflow, "r-test", "Install Rust MSRV")
    assert rust_step["with"] == {"toolchain": "1.85.0"}
    assert "Requires Rust 1.85" in (R_PACKAGE / "README.md").read_text()
    windows_target = named_step(workflow, "r-test", "Install Windows GNU Rust target")
    assert windows_target["if"] == "runner.os == 'Windows'"
    assert windows_target["run"] == "rustup target add x86_64-pc-windows-gnu"


def test_js_distribution_license_and_wasm_pack_version_are_pinned() -> None:
    manifest = tomllib.loads(
        (REPO_ROOT / "crates" / "ci-js" / "Cargo.toml").read_text()
    )
    assert manifest["package"]["license"] == "MIT"
    assert (REPO_ROOT / "crates" / "ci-js" / "LICENSE").read_text() == (
        REPO_ROOT / "LICENSE"
    ).read_text()

    workflow = load_workflow("js.yml")
    wasm_step = named_step(workflow, "js-test", "Install wasm-pack")
    assert wasm_step["with"] == {"version": "v0.15.0"}


def test_js_uses_one_npm_project() -> None:
    js = REPO_ROOT / "crates" / "ci-js"
    assert not (js / "tests" / "package.json").exists()
    assert not (js / "tests" / "package-lock.json").exists()

    workflow = load_workflow("js.yml")
    for job_name in ("js-lint", "js-test"):
        job = workflow["jobs"][job_name]
        setup = next(
            step for step in job["steps"] if step.get("uses") == "actions/setup-node@v4"
        )
        assert setup["with"]["cache-dependency-path"] == (
            "crates/ci-js/package-lock.json"
        )
        install = next(step for step in job["steps"] if step.get("run") == "npm ci")
        assert install["working-directory"] == "crates/ci-js"

    lint = workflow["jobs"]["js-lint"]
    for command in ("npx prettier --check .", "npx eslint ."):
        step = next(step for step in lint["steps"] if step.get("run") == command)
        assert step["working-directory"] == "crates/ci-js"

    test = workflow["jobs"]["js-test"]
    npm_test = next(step for step in test["steps"] if step.get("run") == "npm test")
    assert npm_test["working-directory"] == "crates/ci-js"


def test_r_workflow_checks_the_built_source_archive_with_warnings_as_errors() -> None:
    workflow = load_workflow("r.yml")
    check_step = named_step(workflow, "r-test", "Build and check source package")
    command = check_step["run"]
    assert isinstance(command, str)
    assert "devtools::build" in command
    assert "devtools::check_built" in command
    assert 'error_on = "warning"' in command


def test_r_package_completes_the_mit_license_template() -> None:
    description = (REPO_ROOT / "crates" / "ci-r" / "DESCRIPTION").read_text()
    assert "License: MIT + file LICENSE" in description
    assert (REPO_ROOT / "crates" / "ci-r" / "LICENSE").read_text() == (
        "YEAR: 2026\nCOPYRIGHT HOLDER: pgmpy\n"
    )


def test_r_builds_use_the_packaged_lockfile_and_keep_linting_enabled() -> None:
    for makevars in ("Makevars.in", "Makevars.win.in"):
        contents = (REPO_ROOT / "crates" / "ci-r" / "src" / makevars).read_text()
        assert "cargo build --locked" in contents
        assert "cargo run --locked" in contents

    lintr_config = (REPO_ROOT / "crates" / "ci-r" / ".lintr").read_text()
    assert "object_usage_linter = NULL" not in lintr_config


def test_r_vendor_archive_matches_the_locked_crate_set_and_declares_licenses() -> None:
    """Every locked registry crate is vendored with a Cargo license declaration."""
    manifests = vendored_crate_manifests()
    assert set(manifests) == registry_crates_from_lockfile()
    assert EXTENDR_CRATES <= {name for name, _ in manifests}
    with tarfile.open(VENDOR_ARCHIVE, "r:xz") as archive:
        members = {member.name for member in archive.getmembers()}
    for (name, _), manifest in manifests.items():
        if name in PLATFORM_STUBBED_CRATES:
            continue
        license_expression = manifest.get("license", "")
        license_file = manifest.get("license-file", "")
        assert isinstance(license_expression, str)
        assert isinstance(license_file, str)
        assert license_expression.strip() or license_file.strip()
        if license_file:
            assert f"vendor/{name}/{license_file}" in members


def test_r_vendor_script_is_reproducible() -> None:
    script = (R_PACKAGE / "tools" / "vendor_crates.sh").read_text()
    assert "cargo vendor-filterer" in script
    for platform in (
        "x86_64-unknown-linux-gnu",
        "aarch64-unknown-linux-gnu",
        "x86_64-apple-darwin",
        "aarch64-apple-darwin",
        "x86_64-pc-windows-gnu",
    ):
        assert platform in script


def test_r_package_includes_the_upstream_extendr_mit_notice() -> None:
    """Redistributed extendr crates retain their upstream copyright and MIT terms."""
    notice = THIRD_PARTY_NOTICE.read_text(encoding="utf-8")
    assert "https://github.com/extendr/extendr" in notice
    assert all(crate in notice for crate in EXTENDR_CRATES)
    assert "Copyright (c) 2021 The Extendr contributors (See CONTRIBUTORS.md)" in notice
    for contributor in (
        "Andy Thomason",
        "Thomas Down",
        "Mossa Merhi Reimert",
        "Claus O. Wilke",
        "Hiroaki Yutani",
        "Ilia Kosenkov",
        "Daniel Falbel",
        "Genomics PLC",
    ):
        assert contributor in notice
    assert (
        "Permission is hereby granted, free of charge, to any person obtaining a copy"
        in notice
    )
    assert (
        "The above copyright notice and this permission notice shall be included"
        in notice
    )


def test_r_source_archive_excludes_python_cache_artifacts() -> None:
    """R CMD build must not distribute local Python bytecode or cache directories."""
    buildignore = (R_PACKAGE / ".Rbuildignore").read_text(encoding="utf-8")
    assert r"^tools/__pycache__$" in buildignore
    assert r"^[^/]+/.*[.]pyc$" in buildignore


def test_ci_omits_unused_openblas_and_redundant_core_build() -> None:
    docs = (REPO_ROOT / ".github" / "workflows" / "docs.yml").read_text()
    assert "libopenblas-dev" not in docs

    rust = load_workflow("rust.yml")
    steps = rust["jobs"]["rust_test"]["steps"]
    commands = [step.get("run", "") for step in steps if isinstance(step, dict)]
    assert not any("cargo build -p fastcit-core" in command for command in commands)
    assert any("cargo test -p fastcit-core" in command for command in commands)


def test_rust_distribution_dependency_tree_is_minimal() -> None:
    root = tomllib.loads((REPO_ROOT / "Cargo.toml").read_text())
    r_rust = tomllib.loads((R_RUST / "Cargo.toml").read_text())
    expected = {"version": "0.18.0", "default-features": False}
    assert root["workspace"]["dependencies"]["statrs"] == expected
    assert r_rust["workspace"]["dependencies"]["statrs"] == expected
    faer = {"version": "0.24", "default-features": False, "features": ["std", "linalg"]}
    assert root["workspace"]["dependencies"]["faer"] == faer
    assert r_rust["workspace"]["dependencies"]["faer"] == faer
    core = tomllib.loads((REPO_ROOT / "crates" / "ci-core" / "Cargo.toml").read_text())
    for forbidden in ("rayon", "rand", "getrandom"):
        assert forbidden not in core["dependencies"]

    js = tomllib.loads((REPO_ROOT / "crates" / "ci-js" / "Cargo.toml").read_text())
    assert "getrandom" not in js["dependencies"]
    assert "getrandom" not in js.get("target", {}).get(
        'cfg(target_arch = "wasm32")', {}
    ).get("dependencies", {})


def test_published_crates_declare_license_and_repository() -> None:
    for relative in (
        "crates/ci-core/Cargo.toml",
        "crates/ci-python/Cargo.toml",
        "crates/ci-js/Cargo.toml",
    ):
        package = tomllib.loads((REPO_ROOT / relative).read_text())["package"]
        assert package["license"] == "MIT"
        assert package["repository"] == "https://github.com/pgmpy/ci-tests"
        assert "Your Team" not in " ".join(package.get("authors", []))


@pytest.mark.parametrize("workspace", [REPO_ROOT, R_RUST], ids=["bindings", "r"])
def test_lockfiles_track_workspace_package_versions(workspace: Path) -> None:
    """A locked build must use the versions declared by its workspace members."""
    manifest = tomllib.loads((workspace / "Cargo.toml").read_text())
    members = [workspace / member for member in manifest["workspace"]["members"]]
    if "package" in manifest:
        members.append(workspace)
    packages = [
        tomllib.loads((member / "Cargo.toml").read_text())["package"]
        for member in members
    ]
    locked = tomllib.loads((workspace / "Cargo.lock").read_text())["package"]
    locked_local_versions = {
        (package["name"], package["version"])
        for package in locked
        if "source" not in package
    }
    assert {
        (package["name"], package["version"]) for package in packages
    } <= locked_local_versions
