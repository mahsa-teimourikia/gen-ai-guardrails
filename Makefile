PYTHON ?= python3

.PHONY: help setup-learner setup-contributor test notebooks notebooks-changed links quiz-test pages clean

help:
	@echo "Available targets:"
	@echo "  setup-learner      Create a learner virtual environment"
	@echo "  setup-contributor  Create a contributor virtual environment"
	@echo "  test               Run Python tests"
	@echo "  notebooks          Execute curriculum notebooks"
	@echo "  notebooks-changed  Execute notebooks changed from origin/main"
	@echo "  links              Validate internal Markdown and quiz links"
	@echo "  quiz-test          Run quiz tests"
	@echo "  pages              Build and smoke test the Learning Hub"
	@echo "  clean              Show cleanup guidance"

setup-learner:
	$(PYTHON) -m venv .venv
	.venv/bin/python -m pip install --upgrade pip
	.venv/bin/python -m pip install -e '.[learner]'

setup-contributor:
	$(PYTHON) -m venv .venv
	.venv/bin/python -m pip install --upgrade pip
	.venv/bin/python -m pip install -e '.[contributor]'

test:
	PYTHONPATH=. $(PYTHON) -m pytest -q

notebooks:
	PYTHONPATH=. $(PYTHON) -m pytest -q tests/test_notebooks.py

notebooks-changed:
	PYTHONPATH=. $(PYTHON) scripts/run_notebooks.py --base origin/main

links:
	$(PYTHON) scripts/validate_links.py

quiz-test:
	cd quiz && npm test

pages:
	npm run check:pages-links
	npm run test:pages

clean:
	@echo "The virtual environment and generated artifacts are intentionally not removed automatically."
