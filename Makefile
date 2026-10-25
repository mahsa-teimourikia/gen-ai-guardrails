UV ?= uv

.PHONY: help setup-learner setup-contributor test notebooks notebooks-changed links quiz-test pages serve-hub validate clean

help:
	@echo "Available targets:"
	@echo "  setup-learner      Create a learner virtual environment"
	@echo "  setup-contributor  Sync the locked contributor and web environments"
	@echo "  test               Run Python tests"
	@echo "  notebooks          Execute curriculum notebooks"
	@echo "  notebooks-changed  Execute notebooks changed from origin/main"
	@echo "  links              Validate internal Markdown and quiz links"
	@echo "  quiz-test          Run quiz tests"
	@echo "  pages              Build and smoke test the Learning Hub"
	@echo "  serve-hub          Serve the built Learning Hub locally"
	@echo "  validate           Run the complete release validation gate"
	@echo "  clean              Show cleanup guidance"

setup-learner:
	$(UV) sync --locked --extra learner

setup-contributor:
	$(UV) sync --locked --extra contributor
	npm ci

test:
	PYTHONPATH=. $(UV) run --locked --extra contributor pytest -q

notebooks:
	PYTHONPATH=. $(UV) run --locked --extra contributor pytest -q tests/test_notebooks.py

notebooks-changed:
	PYTHONPATH=. $(UV) run --locked --extra contributor python scripts/run_notebooks.py --base origin/main

links:
	node scripts/validate-learning-links.mjs

quiz-test:
	cd quiz && npm test

pages:
	npm run check:pages-links
	npm run test:pages

serve-hub:
	$(UV) run --locked --extra contributor python -m http.server 8000 --directory out

validate:
	$(UV) lock --check
	$(UV) sync --locked --extra contributor
	$(UV) pip check
	PYTHONPATH=. $(UV) run --locked --extra contributor python -m compileall -q curriculum scripts tests
	PYTHONPATH=. $(UV) run --locked --extra contributor pytest -q
	node --check quiz/app.js
	node --check quiz/grading.js
	node --check quiz/questions.js
	node --check scripts/copy-quiz-to-pages.mjs
	node --check scripts/validate-learning-links.mjs
	node --check tests/pages-smoke.mjs
	node scripts/validate-learning-links.mjs
	npm --prefix quiz test
	npm run test:pages

clean:
	@echo "The virtual environment and generated artifacts are intentionally not removed automatically."
