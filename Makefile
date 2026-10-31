.PHONY: install test lint smoke check api ui up
install:
	python -m pip install -e ".[dev]"
test:
	pytest
lint:
	ruff check src tests app scripts
smoke:
	python scripts/smoke_fake_adapter.py
check: lint test smoke
api:
	uvicorn acbs.api.main:app --reload --port 8000
ui:
	streamlit run app/streamlit_app.py
up:
	docker compose up --build
