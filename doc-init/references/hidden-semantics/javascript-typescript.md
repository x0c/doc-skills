# JavaScript/TypeScript Implicit Semantics Scan

For JavaScript/TypeScript projects, especially Node.js, NestJS, Express/Koa, Next.js, React/Vue, GraphQL, frontend build tools, and serverless scenarios.

## Common hidden mechanisms

- Middleware / interceptor / guard / pipe / filter: automatic logic before and after requests enter business methods.
- Decorator / metadata: NestJS decorator, class-validator, TypeORM decorator, Angular decorator, custom decorator.
- Hook / lifecycle: React hook, Vue lifecycle, Next.js data fetching, NestJS module lifecycle, ORM hook.
- Routing and file conventions: Next.js app/pages router, API route, dynamic route, framework convention.
- Async events: EventEmitter, queue worker, cron, webhook, message consumer, promise chain, observable.
- Runtime config: `.env*`, feature flag, tenant config, build-time env vs runtime env.
- Codegen: GraphQL codegen, OpenAPI client, Prisma client, protobuf, typed routes.
- State and cache: React query, Redux/Zustand, server cache, edge cache, Redis wrapper.

## Scan entry points and file clues

- Build: `package.json`, `pnpm-lock.yaml`, `yarn.lock`, `tsconfig.json`, `vite.config.*`, `next.config.*`.
- Framework: `main.ts`, `app.module.ts`, `middleware.ts`, `pages/`, `app/`, `routes/`, `server.ts`.
- Conventions: `*.decorator.ts`, `*.guard.ts`, `*.interceptor.ts`, `*.pipe.ts`, `*.filter.ts`, `*.middleware.ts`.
- ORM/codegen: `schema.prisma`, `graphql/**/*.graphql`, `openapi*.yaml`, `generated/`.
- Config: `.env*`, `config/*.ts`, feature flag client, runtime config loader.

## Typical AI pitfalls

- Changing only handler/controller while ignoring auth, validation, transform, rate limiting, or context injection in guard/interceptor/pipe/middleware.
- Treating build-time env as runtime env so deployed behavior differs from local.
- Forgetting to regenerate client/types after changing GraphQL/OpenAPI schema.
- Changing only component state on the frontend while forgetting query cache, server action, route cache, or edge cache.
- Misjudging server/client boundaries in Next.js/React/Vue so code runs on the wrong end.
- Ignoring async event / queue worker and treating an API return as business completion.

## What to write into the Knowledge Base

- This domain’s request chain: route/controller → middleware/guard/interceptor/pipe/filter → service → event/worker.
- Which decorators, schemas, hooks, and codegen change the behavior of explicit code.
- Env/config/cache rules for this domain, plus local vs build vs runtime differences.
- Validation paths when changing APIs, schemas, frontend state, or async tasks.

## When to extract a Guide

- AuthN/AuthZ, request context, error handling, cache, routing conventions, codegen, or async queues are shared across domains.
- Next.js/React/Vue runtime boundaries, cache strategy, or release validation paths affect multiple modules.
- GraphQL/OpenAPI/Prisma generation flows are cross-domain development constraints.

## Q&A follow-up templates

- I see `[middleware/guard/interceptor/pipe]` run before `[handler]`—what business context does it inject or modify?
- Does `[decorator/schema]` automatically validate, transform, authorize, or register routes? What happens if it is misused?
- After changing `[API/schema/model]`, must codegen run? Are generated artifacts committed?
- Is `[env/config/feature flag]` read at build time or runtime? Is behavior consistent across environments?
- After the API returns, do queue/event/webhook steps still finish the business? How do you verify async results?
