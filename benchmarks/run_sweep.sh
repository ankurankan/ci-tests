#!/usr/bin/env bash
# Run the whole sweep benchmark: data, Python, dowhy (optional), R, summary.
#
# Usage: benchmarks/run_sweep.sh OUTDIR [--quick]
#
# Environment variables:
#   PYTHON            main Python interpreter (default python3)
#   PYTHON_DOWHY      Python 3.11 interpreter with dowhy; when unset or not runnable, the dowhy run is skipped
#   PYTHONPATH_DOWHY  PYTHONPATH for the dowhy run only (default: the value of PYTHONPATH)
#   RSCRIPT           Rscript command (default Rscript); one command, not a command with arguments
# The script checks the interpreters and the R packages first, so that a missing package stops it at once.
# The script stops at the first error. It never changes the power profile.
set -euo pipefail

if [ $# -lt 1 ] || [ $# -gt 2 ] || { [ $# -eq 2 ] && [ "$2" != "--quick" ]; }; then
  echo "Usage: $0 OUTDIR [--quick]" >&2
  exit 2
fi
OUT=$1
QUICK=("${@:2}")
HERE=$(cd "$(dirname "$0")" && pwd)
PYTHON=${PYTHON:-python3}
PYTHON_DOWHY=${PYTHON_DOWHY:-}
RSCRIPT=${RSCRIPT:-Rscript}
mkdir -p "$OUT"

step() { printf '\n[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
fail() { echo "ERROR: step failed: $1" >&2; exit 1; }

# Run a step: run "$1" (its name) with the command in the other arguments.
run() {
  local name=$1
  shift
  step "$name"
  "$@" || fail "$name"
}

CPUS=$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 1)
PIN_PY=()
PIN_R=()
if command -v taskset >/dev/null 2>&1; then
  PIN_R=(taskset -c 0-3)
  if [ "$CPUS" -ge 12 ]; then
    PIN_PY=(taskset -c 0-11)
  fi
fi
if [ ${#PIN_PY[@]} -gt 0 ]; then
  echo "CPU pinning: Python on CPUs 0-11, R on CPUs 0-3."
else
  echo "CPU pinning: none for Python (needs taskset and at least 12 CPUs; found $CPUS)."
  if [ ${#PIN_R[@]} -gt 0 ]; then
    echo "CPU pinning: R on CPUs 0-3."
  else
    echo "CPU pinning: none for R (no taskset)."
  fi
fi

# Power check (Linux only, warns and never changes anything).
AC=""
for f in /sys/class/power_supply/*/online; do
  [ -e "$f" ] && AC=$(cat "$f") && break
done
if [ -n "$AC" ] && command -v powerprofilesctl >/dev/null 2>&1; then
  PROFILE=$(powerprofilesctl get 2>/dev/null || echo unknown)
  echo "Power: AC online = $AC, profile = $PROFILE."
  [ "$AC" = "1" ] || echo "WARNING: the machine is not on AC power."
  [ "$PROFILE" = "performance" ] || echo "WARNING: the power profile is not 'performance'."
else
  echo "Power: no AC state or powerprofilesctl found; check the power state by hand."
fi
echo "Load: $(uptime | sed 's/.*load average[s]*: //'). Wait for a load below 1.5 before a full run."

# Preflight: fail now, not after the long Python step.
step "Preflight"
pre_fail() { echo "ERROR: preflight: $*" >&2; exit 1; }
"$PYTHON" -c "import fastcit, numpy, pandas" >/dev/null 2>&1 \
  || pre_fail "PYTHON ($PYTHON) cannot import fastcit, numpy and pandas. Install them or set PYTHON."
echo "Python engines that import in $PYTHON: $("$PYTHON" -c "import sys; sys.path.insert(0, sys.argv[1]); import bench_python as bp; print(', '.join(e for e in bp.ENGINE_MODULES if bp.importable(e) and e != 'fastcit (yates)'))" "$HERE" 2>/dev/null || echo unknown)"
if [ -n "$PYTHON_DOWHY" ]; then
  env PYTHONPATH="${PYTHONPATH_DOWHY-${PYTHONPATH-}}" "$PYTHON_DOWHY" -c "import dowhy.gcm.independence_test, fastcit" >/dev/null 2>&1 \
    || pre_fail "PYTHON_DOWHY ($PYTHON_DOWHY) cannot import dowhy.gcm.independence_test and fastcit. Fix it or unset PYTHON_DOWHY."
  echo "dowhy interpreter: $PYTHON_DOWHY (dowhy and fastcit import)."
fi
command -v "$RSCRIPT" >/dev/null 2>&1 \
  || pre_fail "RSCRIPT ($RSCRIPT) is not a single command on the PATH. For conda, write a wrapper script and set RSCRIPT to it."
"$RSCRIPT" -e 'p <- c("fastcit", "jsonlite", "pcalg", "bnlearn", "dHSIC", "Rfast", "ppcor", "comets"); bad <- p[!vapply(p, requireNamespace, logical(1), quietly = TRUE)]; if (length(bad)) { cat("missing R packages:", bad, "\n"); quit(status = 1) }' \
  || pre_fail "RSCRIPT ($RSCRIPT) cannot load every R package."
echo "R packages: all installed."

run "sweep_data.py" "$PYTHON" "$HERE/sweep_data.py" "$OUT"
run "Python sweep (sweep_python.py)" "${PIN_PY[@]+"${PIN_PY[@]}"}" "$PYTHON" "$HERE/sweep_python.py" "$OUT" ${QUICK[@]+"${QUICK[@]}"}

DOWHY_DONE=no
if [ -z "$PYTHON_DOWHY" ]; then
  step "dowhy sweep skipped: PYTHON_DOWHY is not set"
elif ! "$PYTHON_DOWHY" -c 'import sys' >/dev/null 2>&1; then
  step "dowhy sweep skipped: PYTHON_DOWHY ($PYTHON_DOWHY) does not run"
else
  step "dowhy sweep (sweep_python.py, $PYTHON_DOWHY)"
  env PYTHONPATH="${PYTHONPATH_DOWHY-${PYTHONPATH-}}" \
    "${PIN_PY[@]+"${PIN_PY[@]}"}" "$PYTHON_DOWHY" "$HERE/sweep_python.py" "$OUT" \
    --engines dowhy,fastcit --rows gcm --out sweep-python-dowhy.json ${QUICK[@]+"${QUICK[@]}"} \
    || fail "dowhy sweep (sweep_python.py)"
  DOWHY_DONE=yes
fi

run "R sweep (sweep_r.R)" "${PIN_R[@]+"${PIN_R[@]}"}" "$RSCRIPT" "$HERE/sweep_r.R" "$OUT" ${QUICK[@]+"${QUICK[@]}"}
run "summarize_sweep.py" "$PYTHON" "$HERE/summarize_sweep.py" "$OUT"

step "Done."
echo "Results in $OUT:"
echo "  sweep.json, sweep.md   summary"
echo "  sweep-python.json, sweep-r.json   run files"
[ "$DOWHY_DONE" = yes ] && echo "  sweep-python-dowhy.json   dowhy run file"
if [ ${#QUICK[@]} -gt 0 ]; then
  echo "This was a quick run. Do not commit its files."
else
  echo "Copy these files into benchmarks/results/ and commit them:"
  echo "  sweep-python.json sweep-r.json sweep.json sweep.md$([ "$DOWHY_DONE" = yes ] && echo ' sweep-python-dowhy.json')"
fi
