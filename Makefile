# pip tools
.PHONY: lock
lock:
	pip-compile requirements.in -o requirements.txt
	pip-compile requirements.dev.in -o requirements.dev.txt





# run the application
.PHONY: run
run:
	uvicorn src.main:app




# code quality

# fix formatting / and order imports
.PHONY: fix
fix:
	python -m black ./
	python -m isort ./


# check type annotations
.PHONY: types
types:
	python -m mypy --check-untyped-defs ./


# check everything
.PHONY: check
check:
	python -m ruff ./
	python -m black --check ./
	python -m isort --check ./
	python -m mypy --check-untyped-defs ./




# just a tool for frontend team
.PHONY: frontend
frontend:
	alembic upgrade head
	uvicorn src.main:app
