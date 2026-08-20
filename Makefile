.PHONY: test compile demo generate benchmark chaos clean

compile:
	python3 -m compileall -q atlas_core apps

test: compile
	python3 -m pytest

demo:
	python3 -m apps.cli.atlas_cli demo --customers 25 --batch-size 10

generate:
	python3 -m apps.cli.atlas_cli generate --seed 42 --customers 100 --output golden-datasets/generated

benchmark:
	python3 -m apps.cli.atlas_cli benchmark --rows 10000

chaos:
	python3 -m apps.cli.atlas_cli chaos worker-crash --seed 42

clean:
	rm -rf .atlas .pytest_cache __pycache__ atlas_core/__pycache__ apps/__pycache__ apps/cli/__pycache__
