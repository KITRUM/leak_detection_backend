# alias of cq is code qualit
.PHONY: cq
cq:
	black ./ && ruff ./ && isort --check ./

