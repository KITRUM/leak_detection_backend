.PHONY: run
run:
	uvicorn src.main:app

# alias of cq is code qualit
.PHONY: cq
cq:
	python -m black ./ && \
	python -m ruff ./ && \
	python -misort --check ./

.PHONY: types
types:
	python -m mypy --check-untyped-defs ./

