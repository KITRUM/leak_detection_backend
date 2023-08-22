.PHONY: run
run:
	uvicorn src.main:app


# alias of cq is code qualit
.PHONY: cq
cq:
	python -m black ./
	python -m ruff ./
	python -m isort ./


.PHONY: types
types:
	python -m mypy --check-untyped-defs ./



.PHONY: check
check:
	python -m ruff ./
	python -m black --check ./
	python -m isort --check ./
	python -m mypy --check-untyped-defs ./


.PHONY: frontend
frontend:
	alembic upgrade head
	uvicorn src.main:app
