.PHONY: lint test mypy all docs clean

lint:
	ruff check .

test:
	pytest tests/ -v

mypy:
	mypy flamapy_dev.py commands/

all: lint mypy test

docs:
	python flamapy_dev.py docs generate -o CLI_REFERENCE.md
	@echo "✓ CLI_REFERENCE.md generated"

clean:
	rm -rf build/ dist/ *.egg-info __pycache__ .pytest_cache .mypy_cache
