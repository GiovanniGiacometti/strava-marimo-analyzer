# https://github.com/casey/just

set quiet

dev-sync:
    uv sync --all-extras --cache-dir .uv_cache

format:
	uv run ruff format app.py

edit:
	uv run marimo edit app.py

run:
	uv run marimo run app.py

export:
	marimo export html-wasm app.py -o wasm --mode run

serve:
	python -m http.server --directory wasm
	