# pip tools
.PHONY: lock
lock:
	pip-compile requirements.in -o requirements.txt


.PHONY: lock_dev
lock_dev:
	pip-compile requirements.dev.in -o requirements.dev.txt





# run the application
.PHONY: run
run:
	uvicorn src.main:app




# code quality

# alias of cq is code quality
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
