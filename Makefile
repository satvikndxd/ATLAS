.PHONY: compile test demo generate benchmark chaos frontend api-smoke verify-all clean

compile:
	python3 -m compileall -q atlas_core apps tests

test: compile
	python3 -m pytest -q

demo:
	python3 -m apps.cli.atlas_cli demo --customers 25 --batch-size 10

generate:
	python3 -m apps.cli.atlas_cli generate --seed 42 --customers 100 --output golden-datasets/generated

benchmark:
	python3 -m apps.cli.atlas_cli benchmark --rows 10000

chaos:
	python3 -m apps.cli.atlas_cli chaos worker-crash --seed 42

frontend:
	cd apps/web-console && pnpm install --frozen-lockfile && pnpm build

api-smoke:
	@echo "Run scripts/api-smoke.sh with a local control plane"

verify-all:
	./scripts/verify-all.sh

clean:
	rm -rf .atlas .pytest_cache __pycache__ atlas_core/__pycache__ apps/__pycache__ apps/cli/__pycache__ apps/control-plane-dotnet/bin apps/control-plane-dotnet/obj apps/control-plane-dotnet.Tests/bin apps/control-plane-dotnet.Tests/obj apps/web-console/dist apps/web-console/tsconfig.tsbuildinfo crates/fingerprint/target
