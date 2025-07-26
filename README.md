## How to run app:
```bash
uvicorn app.main:app --host localhost --port 8002 --reload
```

## Upgrade migrate
```bash
alembic revision --autogenerate -m "describe your changes"
```

## Apply migrate
```bash
alembic upgrade head
```