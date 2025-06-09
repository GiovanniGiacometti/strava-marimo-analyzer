# https://github.com/casey/just

dev-sync:
    uv sync --all-extras --cache-dir .uv_cache

format:
	uv run ruff format visualizer.py

install-hooks:
	uv run pre-commit install