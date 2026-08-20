#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
failures=0
skips=0

run_step() {
  local name="$1"; shift
  printf '\n=== %s ===\n' "$name"
  if "$@"; then
    echo "PASS — $name"
  else
    local code=$?
    echo "FAIL — $name (exit $code)"
    failures=$((failures + 1))
  fi
}

skip_step() {
  local name="$1"; local reason="$2"
  echo "SKIPPED — $name: $reason"
  skips=$((skips + 1))
}

run_step "Python compile" python3 -m compileall -q atlas_core apps tests
run_step "Python tests" python3 -m pytest -q
rm -rf /tmp/atlas-verify-demo
run_step "Deterministic demo" python3 -m apps.cli.atlas_cli demo --seed 42 --customers 10 --batch-size 5 --state-dir /tmp/atlas-verify-demo
run_step "Rust tests" bash -lc 'cd crates/fingerprint && cargo test --locked'
run_step "Rust format" bash -lc 'cd crates/fingerprint && cargo fmt --check'
run_step "Rust clippy" bash -lc 'cd crates/fingerprint && cargo clippy --locked -- -D warnings'
run_step ".NET restore/build" dotnet build apps/control-plane-dotnet/Atlas.ControlPlane.csproj
run_step ".NET tests" dotnet test apps/control-plane-dotnet.Tests/Atlas.ControlPlane.Tests.csproj
run_step "Frontend frozen install/build" bash -lc 'cd apps/web-console && pnpm install --frozen-lockfile && pnpm build'

if command -v docker >/dev/null 2>&1; then
  run_step "Compose configuration" docker compose -f infrastructure/docker-compose.yml config
  skip_step "Live database contract tests" "vendor database fixtures are not enabled by default; run the live-db CI workflow"
else
  skip_step "Compose and live database tests" "Docker is not installed in this environment"
fi

if [ "$failures" -eq 0 ]; then
  if [ "$skips" -gt 0 ]; then
    echo "ATLAS VERIFICATION: PASS WITH $skips EXPLICIT SKIP(S)"
  else
    echo "ATLAS VERIFICATION: PASS"
  fi
  exit 0
fi

echo "ATLAS VERIFICATION: FAIL ($failures failing step(s), $skips skipped step(s))"
exit 1
