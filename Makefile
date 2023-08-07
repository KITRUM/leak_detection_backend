.PHONY: run
run:
	uvicorn src.main:app

# alias of cq is code qualit
.PHONY: cq
cq:
	black ./ && ruff ./ && isort --check ./

