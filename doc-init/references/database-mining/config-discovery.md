# Config Discovery

This document defines how to discover database connections. Do not turn it into a language tutorial; identify the project ecosystem first, then find the connection sources the project actually uses.

## Scan principles

- Find the runtime entry and profile/env selection mechanism first, then decide which config is actually in effect.
- Scan source config, environment-variable templates, container/deploy config, test config, and ORM/data-source initialization code together.
- A secret reference in a config file is not a plaintext connection; record the reference chain, and ask the user for a read-only connection when needed.
- In multi-data-source projects, distinguish business DBs, log DBs, metadata DBs, test DBs, read-only DBs, and migration DBs.
- By default, output full candidate values so connection tests can run directly; mask only when the user asks or the environment is not a test environment.

## Common entry cheat sheet

These are reminders only—do not treat the list as exhaustive:

| Ecosystem | Common clues |
|---|---|
| Java/Kotlin | `application*.yml/properties`, Spring profile, `DataSource`, JDBC URL, MyBatis/JPA config, Docker/K8s secret |
| .NET | `appsettings*.json`, `ConnectionStrings`, UserSecrets, `DbContext`, Dapper/ADO.NET init, launch profile |
| JS/TS | `.env*`, Prisma/TypeORM/Sequelize/Knex config, Nest/Next runtime config, Docker/compose |
| Python | Django settings, SQLAlchemy/FastAPI config, Alembic, Celery/worker env, `.env*` |
| Go | viper/envconfig, `config*.yaml/json/toml`, `database/sql` init, gorm/sqlx config, Docker/compose |
| General | `docker-compose*.yml`, Helm/K8s manifests, Terraform, CI variables, README startup notes, testcontainer config |

## Output fields

Connection discovery only emits candidates; it does not assert that they work:

```json
{
  "source_file": "config/appsettings.Development.json",
  "source_key": "ConnectionStrings.Main",
  "db_type_hint": "postgresql",
  "value": "postgresql://user:password@localhost:5432/app",
  "profile_or_env": "Development",
  "confidence": "medium",
  "notes": ["References env var DB_PASSWORD; if no plaintext value is found in the repo, ask the user to supply it"]
}
```

## When to ask the user

Ask only when required information is missing; do not interrupt just to “confirm”:

- Only a secret name exists, with no locally usable value.
- Multiple candidate connections exist and it is unclear which is read-only or a test environment.
- The connection points at production or likely production, with no read-only guarantee.
- The project strongly depends on database facts, but no connection source exists.

When the user forbids questions, record “database evidence missing” and the reason, then continue building low-confidence knowledge from code, human materials, and runtime validation.
