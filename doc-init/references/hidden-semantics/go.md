# Go Implicit Semantics Scan

For Go projects, especially web services, microservices, CLIs, job systems, gRPC, codegen, and middleware scenarios.

## Common hidden mechanisms

- Middleware / interceptor: HTTP middleware, gRPC interceptor, router group middleware.
- `context.Context`: user, tenant, trace, deadline, cancel, transaction, request-scoped value.
- Interface wrapper: decorator-style wrappers, client wrapper, repository wrapper, mock/generated implementation.
- `init` / package side effect: route registration, driver registration, config loading, global variable init.
- Build tag / go generate: platform differences, generated code, wire/mock/protobuf/openapi.
- Goroutine / channel: async execution, concurrency safety, context cancel, background compensation.
- Config injection: env, viper, flag, yaml, remote config, feature flag.
- DB/cache wrappers: transaction helper, repository pattern, sql hook, cache-aside wrapper.

## Scan entry points and file clues

- Build: `go.mod`, `go.sum`, `Makefile`, `Taskfile.yml`, `Dockerfile`.
- Entry: `cmd/**/main.go`, `internal/`, `pkg/`, `server.go`, `router.go`, `wire.go`.
- Middleware: `middleware/`, `interceptor/`, `handler/`, `router/`.
- Generated: `//go:generate`, `*.pb.go`, `*_gen.go`, `wire_gen.go`, `mock_*.go`.
- Conditional compile: `//go:build`, `// +build`.
- Config: `config/`, `*.yaml`, `.env*`, flag/env loader.

## Typical AI pitfalls

- Changing only the handler while ignoring auth, tenant, trace, transaction, or recover injected by middleware/interceptor.
- Not passing or incorrectly reusing `context.Context`, losing timeout, cancel, tenant, trace, or permission.
- Changing interface callers without finding the real implementation or wrapper, misjudging actual execution logic.
- Ignoring `init` registration, side-effect imports, build tags, or go generate, so it runs locally but not on the target platform.
- Using request context or non-thread-safe objects inside goroutines, making async logic unstable.
- Forgetting to regenerate code after changing proto/openapi/sqlc/ent/gorm models.

## What to write into the Knowledge Base

- Real wiring and wrapper chains for this domain’s handler/service/repository/client.
- Which context values this domain requires, who writes them, who reads them, and how they pass through async paths.
- Which generated code, build tags, and init registrations affect this domain’s entry points.
- Which proto/openapi/sqlc/config/middleware must be updated together when changing this domain.

## When to extract a Guide

- context, middleware/interceptor, codegen, transaction helper, config loading, or async task patterns are shared across domains.
- The wrapper chain or DI/wire assembly is complex enough that a single KB cannot explain it clearly.
- Build tag / platform differences affect multiple modules.

## Q&A follow-up templates

- I see `[middleware/interceptor]` wrapping `[handler/rpc]`—which context values does it inject?
- What is the real implementation and wrapper chain for `[interface]`? Which calls must not bypass the wrapper?
- Is `[context value]` still valid in an async goroutine? What is the project’s passing convention?
- After changing `[proto/openapi/sqlc/ent]`, must go generate run? Are generated artifacts committed?
- Are there build tags or platform differences that send different environments down different implementations?
