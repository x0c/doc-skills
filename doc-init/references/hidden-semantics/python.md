# Python Implicit Semantics Scan

For Python projects, especially Django, FastAPI, Flask, Celery, SQLAlchemy, Pydantic, Airflow, data processing, and async task scenarios.

## Common hidden mechanisms

- Decorator: routing, permission, cache, transaction, retry, rate limiting, custom wrapper.
- Context manager / dependency injection: FastAPI dependency, Flask context, Django request/user, database session.
- Metaclass / descriptor / property: model fields, ORM mapping, dynamic attributes.
- Middleware / signal / hook: Django middleware, signals, Flask before/after request, SQLAlchemy events.
- ORM behavior: lazy loading, session flush/commit, model save/delete hook, migration, query filter.
- Contextvars / thread local: request context, tenant/user context, trace.
- Async / task: Celery task, RQ, asyncio, background task, retry policy, beat schedule.
- Settings overrides: `settings.py`, `.env`, pydantic settings, environment variables, test config.

## Scan entry points and file clues

- Build deps: `pyproject.toml`, `requirements*.txt`, `Pipfile`, `poetry.lock`.
- Framework entry: `manage.py`, `settings.py`, `urls.py`, `asgi.py`, `wsgi.py`, `main.py`, `app.py`.
- Convention files: `middleware.py`, `signals.py`, `tasks.py`, `dependencies.py`, `models.py`, `schemas.py`.
- Config: `.env*`, `config.py`, `settings/*.py`.
- Migrations and ORM: `migrations/`, SQLAlchemy model/session, Alembic config.

## Typical AI pitfalls

- Changing only view/handler while ignoring decorator, dependency, middleware, signal, or permission class.
- Changing model fields but forgetting migration, serializer/schema, admin/form, signal, or side-effect tasks.
- Assuming request context or tenant/user context still exists inside Celery/background tasks.
- Confusing SQLAlchemy session flush/commit, Django transaction atomic, and async task commit timing.
- Changing settings without realizing test/dev/prod config sources differ.
- Ignoring property/descriptor/metaclass so a seemingly ordinary field actually has dynamic computation or ORM mapping.

## What to write into the Knowledge Base

- The real execution chain from request/task to ORM/external systems in this domain.
- Which decorators, dependencies, middleware, signals, and ORM hooks run automatically.
- Which contexts must be supplied manually in sync requests, async tasks, tests, and scripts.
- Objects that must be checked together when changing models, schemas, migrations, or tasks.

## When to extract a Guide

- Auth/permission, tenant context, transactions, Celery, settings management, or ORM hooks are shared across domains.
- migration / task / signal usage has project-wide constraints.
- Data processing or async tasks have fixed validation paths and retry/compensation strategies.

## Q&A follow-up templates

- I see `[decorator/dependency/middleware]` changing `[handler]` inputs or permissions—what business responsibility does it carry?
- When does `[signal/hook]` fire? Can it fire more than once, or still run after a transaction fails?
- Can async tasks obtain request/user/tenant context? If not, how does the project pass it?
- After changing `[model/schema]`, must migration, serializer, form, admin, or tasks be updated together?
- Which settings sources override defaults? Which environment config should validation read?
