# RM Release Portal API

FastAPI + MongoDB backend for a Release Management Portal.

## Quickstart

- Copy .env.example to .env and adjust if needed
- Start with Docker

```
docker compose up --build
```

Visit http://localhost:8000/docs

## Local dev

```
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Testing

```
pytest -q
```

## Makefile
- make run | lint | format | test | seed-min | seed-demo
