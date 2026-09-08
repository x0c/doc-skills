# C#/.NET Implicit Semantics Scan

For C#/.NET projects, especially ASP.NET Core, Entity Framework, MediatR, BackgroundService, source generators, and enterprise app scenarios.

## Common hidden mechanisms

- Attribute / filter: Controller/action filter, authorization attribute, validation attribute, custom attribute.
- Middleware pipeline: ASP.NET Core middleware, exception handler, routing, auth, CORS, rate limiting.
- DI lifecycle: singleton/scoped/transient, scope leaks, constructor injection, decorator.
- EF Core: change tracker, global query filter, shadow property, interceptor, save changes hook, lazy loading, migration.
- Async pipeline: `Task`, background service, hosted service, message consumer, retry policy.
- MediatR / pipeline behavior: validation, transaction, logging, permission before/after command/query handlers.
- Configuration binding: `appsettings*.json`, environment variables, options pattern, feature flag.
- Source generator / codegen: protobuf, OpenAPI client, record/source generator, partial class/method.

## Scan entry points and file clues

- Build: `*.csproj`, `*.sln`, `Directory.Build.props`, `global.json`.
- Entry: `Program.cs`, `Startup.cs`, `Controllers/`, `Minimal API` route mapping.
- Pipeline: `Use*` middleware, `Add*` service registration, filters, attributes, MediatR behaviors.
- EF: `DbContext`, `OnModelCreating`, `SaveChanges*`, migrations, interceptors.
- Config: `appsettings*.json`, Options class, `IConfiguration`, environment-specific settings.
- Background: `BackgroundService`, hosted service, queue/message consumer.

## Typical AI pitfalls

- Changing only Controller/Handler while ignoring auth, validation, transaction, logging, or exception handling in middleware/filter/attribute/pipeline behavior.
- Misunderstanding DI lifecycle so a scoped service is held by a singleton or request context is lost.
- Changing an EF entity but forgetting migration, global query filter, shadow property, interceptor, or SaveChanges hook.
- Ignoring the MediatR pipeline and assuming the handler alone holds the full business logic.
- Changing config without distinguishing the effective order of appsettings, environment variables, and Options binding.
- Forgetting async compensation and retry strategy for background services/message consumers.

## What to write into the Knowledge Base

- Middleware/filter/pipeline behavior before and after requests enter Controller/Endpoint/Handler in this domain.
- DI lifecycle, DbContext, EF filter/interceptor, and MediatR behavior this domain depends on.
- How config, feature flags, Options, and environment overrides affect this domain’s behavior.
- Migration, config, and validation paths that must be checked after changing entities, handlers, or background tasks.

## When to extract a Guide

- AuthZ, exception handling, MediatR pipeline, EF Core constraints, config binding, or background-task mechanisms are shared across multiple domains.
- DI lifecycle or DbContext usage rules affect multiple modules.
- A fixed validation path is needed to confirm middleware/filter/interceptor is in effect.

## Q&A follow-up templates

- I see `[attribute/filter/middleware]` wrapping `[endpoint/handler]`—what business responsibility does it carry?
- What does `[MediatR behavior/interceptor]` do before/after the handler? Which calls must not bypass it?
- Is `[DbContext/entity]` affected by a global query filter, shadow property, interceptor, or SaveChanges hook?
- What is the DI lifecycle of `[service]`? Is it safe in background tasks or async processing?
- Does the config value come from appsettings, environment variables, or Options binding? Which environment is the validation source of truth?
