.PHONY: run
run:
	uvicorn src.main:app

# alias of cq is code quality
.PHONY: cq
cq:
	python -m black ./
	python -m ruff ./
	python -m isort --check ./
	python -m mypy --check-untyped-defs ./
