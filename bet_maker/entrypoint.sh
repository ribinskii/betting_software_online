#!/bin/sh

poetry run alembic upgrade head

poetry run uvicorn app.main:app --host 0.0.0.0 --port 8080