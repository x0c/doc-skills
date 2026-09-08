# Java/Kotlin Implicit Semantics Scan

For Java/Kotlin projects, especially Spring, Spring Boot, MyBatis, JPA, Ktor, Micronaut, Quarkus, and similar ecosystems. The goal is not to list framework knowledge, but to find mechanisms that are invisible on the source surface yet change business behavior at runtime.

## Common hidden mechanisms

- AOP / proxy: `@Aspect`, `@Around`, JDK/CGLIB proxy, Spring bean self-invocation failure, interface-proxy vs class-proxy differences.
- Annotation-driven behavior: `@Transactional`, `@Async`, `@Cacheable`, `@Scheduled`, `@EventListener`, validation annotations, permission annotations, custom annotations.
- Transactions and consistency: propagation, read-only transactions, rollback exception types, after-commit events, distributed transactions, partial-failure strategies in batch processing.
- Context: `ThreadLocal`, MDC, tenant context, logged-in user, locale/store/brand context, TraceId.
- ORM / SQL mapping: MyBatis XML, Interceptor, TypeHandler, logical delete, auto-fill, JPA entity listener, lazy loading.
- Generated code: Lombok, MapStruct, protobuf/OpenAPI client, annotation processor, Kotlin data class / coroutine compile semantics.
- Bean lifecycle and config: `@PostConstruct`, BeanPostProcessor, profile, conditional bean, configuration-property binding, starter auto-configuration.
- External contracts: MQ listener, Redis cache, search index, remote RPC/HTTP client, scheduled jobs, async compensation.

## Scan entry points and file clues

- Build: `pom.xml`, `build.gradle*`, `settings.gradle*`, `gradle.properties`.
- Config: `application*.yml`, `bootstrap*.yml`, `META-INF/spring.factories`, `AutoConfiguration.imports`.
- Code: `*Aspect`, `*Interceptor`, `*Filter`, `*Listener`, `*Handler`, `*Resolver`, `*Config`, `*AutoConfiguration`, `*TypeHandler`.
- SQL: `mapper/**/*.xml`, `@Mapper`, `@Select`, `@Update`, MyBatis plugin.
- Generated: `target/generated-sources`, `build/generated`, `@Mapper`, `@Builder`, `@Data`, `@Value`.

## Typical AI pitfalls

- Changing only a Service method body while forgetting transaction propagation, cache annotations, async annotations, or permission annotations so behavior never takes effect.
- Seeing an ordinary method call but missing AOP that does auth, tenant injection, logging, idempotency, locking, or data permission around it.
- `new`-ing objects and bypassing Spring beans, so proxies, config injection, transactions, and lifecycle hooks fail.
- Changing a MyBatis mapper method but missing XML SQL, TypeHandler, logical delete, auto-fill, or sharding-plugin rules.
- Ignoring `ThreadLocal` / MDC / tenant context so local tests pass while real request context is wrong.
- Using Kotlin coroutines / Java async while ignoring context propagation and transaction boundaries.

## What to write into the Knowledge Base

- Which annotations, proxies, contexts, transactions, caches, SQL interceptors, or async mechanisms this domain depends on.
- Which entry points look like ordinary calls but are rewritten by AOP / interceptor / listener.
- Which config, XML, generated classes, cache keys, and context sources must be checked together when changing this domain’s code.
- What business consequences follow from ignoring the mechanism.

## When to extract a Guide

- The same AOP, annotation, sharding plugin, permission interceptor, cache rule, or context mechanism affects multiple domains.
- Changing the mechanism itself affects global behavior, or multiple domain KBs need to cite the same usage constraints.
- The mechanism needs a fixed validation path—e.g. check logs, interceptor results, rewritten SQL, or after-commit events.

## Q&A follow-up templates

- I see `[annotation/aspect/interceptor]` wrapping `[entry]`—what business responsibility does this mechanism carry? Which scenarios must not bypass it?
- If `[class/method]` is called directly or self-invoked in the same class, does that bypass the proxy? Is there a project-agreed correct entry?
- Where is `[ThreadLocal/tenant/user context]` written? How is it guaranteed to exist in async, batch, or MQ consumption?
- When changing `[Mapper/XML/Entity]`, must sharding, logical delete, auto-fill, cache, or indexes be handled together?
- Does `[profile/conditional bean]` behave differently across environments? Which config is authoritative for validation?
