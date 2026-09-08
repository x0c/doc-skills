# Human Intake

This document defines doc-init’s human–AI collaborative interview style. After entering Phase 2, read this file before scanning code; unless the user explicitly forbids questions, do a light Intake first.

## Design goals

doc-init’s strength is not pure automatic static summary, but mutual reinforcement among user experience, existing materials, code evidence, and runtime validation. Code only provides visible structure; real experience usually comes from users and practice.

## Product north star first

Before any code scan, establish the product north star—what the product does, for whom, and what the core loop is. This filters the later domain map: modules found in code with no basis in the product definition are dead-code signals and must not be promoted directly into business domains.

Establishment order: ① read the project’s existing root `AGENTS.md` and follow its product pointers (including cross-repo PRD/roadmap); ② read PRD / north star / roadmap / designs provided by the user or already in the project; ③ if none exist, ask the user for a one-sentence product definition; ④ if still unavailable and the user has forbidden questions → hard stop; do not enter the scan stage (this hard stop is an explicit exception to the “user forbidding questions does not block” principle below; see SKILL.md Step 7a).

## Preflight Intake

Unless the user explicitly says “don’t ask / just generate / test mode / dry run / report only”, do one light Intake before project scanning. Ask at most 5–8 high-leverage questions per round, ordered by impact on doc quality.

Prefer asking about:

- Material entry points: paths or links to requirements / APIs / PRD / designs / test cases / wiki / migration docs.
- Business entry points: how the team names each business domain / line and core concepts; which modules are **most often changed and most error-prone recently** (only to prioritize this session’s deep-write batch—never to shrink the domain map).
- Runtime entry points: start scripts, minimal validation paths, logs / tracing / DB / MQ / job-admin entry points.
- Dependencies and experience: databases, sharding, test data, substitutes for external deps; traps newcomers or AI most often misjudge.

**Questions you must not ask:**

- Do not ask questions that would **trim domain scope**, e.g. “what’s your goal cloning this repo”, “which part do you only want to see”, “what’s your focus”. The domain map always enumerates all domains; user answers only affect which domains go first in this deep-write batch, not which domains appear on the map.
- Do not ask questions you can answer by **reading code or diffing docs yourself**, e.g. “is this design doc outdated”—diff the doc against current code instead of making the user do it. Spend question budget on product essence and experience code cannot see.

## Asking rules

- Do not turn Intake into a long questionnaire; ask first what most changes scan direction.
- If the user cannot answer, do not block; mark “to be filled / low confidence” and continue with code and runtime validation.
- When the user gives material paths, read materials first, then scan code to corroborate; do not guess domains from package/table names alone.
- When persisting oral user info, mark “Source: user supplement”.
- If user input conflicts with code evidence, state the conflict and list it as pending confirmation.
- If the user’s business names differ from code names, table comments, or historical docs, treat the user’s name as the candidate canonical term and others as alias evidence; only split them when confirmed to be different concepts.
- After Intake, still output the knowledge-boundary report, and continue precise Q&A against scan gaps.

## Precise Q&A after scanning

After scanning, only ask for knowledge code cannot see but that affects whether AI can change code correctly. Questions must have concrete anchors—no vague “anything to watch out for”.

Question types:

- Hidden dependencies: “After doing [operation A], is there something that must also happen but isn’t reflected in code?”
- Concept disambiguation: “When do you use [field A] vs [field B]? Can they be passed interchangeably?”
- Business naming alignment: “Code calls it [A], table comments call it [B], you just said [C]—same concept? Which name does the team prefer in final docs?”
- Git historical naming: “History often calls it [A]; current code/tables/APIs call it [B]. Which does the team use now? Is [A] a historical alias or still live?”
- Git historical constraints: “History repeatedly mentions [compat/migration/deprecation/fix]. Is that constraint still valid? What must AI preserve when changing this area?”
- Constraint origin: “I see [concrete code]—why not the intuitive approach [X]?”
- Deep mechanisms: “I see [annotation/decorator/config/middleware/hook/codegen] changes runtime behavior—why must it exist? What breaks if AI only changes explicit code and ignores it?”
- Validation path: “After changing [this domain’s operation], how do veterans usually confirm it really took effect?”

If answers are short, keep probing until constraints are clear enough to write into docs. Question count is discovery-driven; no minimum quota.

## Persistence rules

- User-supplied business names, experience, log entry points, test environments, and validation methods go into the knowledge-boundary report’s “User / materials” section.
- Confirmed canonical terms are used in KB body text; aliases stay lightly at first appearance, entry indexes, or high-risk disambiguation.
- User-supplied domain rules go into the corresponding KB’s business rules, hidden constraints, or validation paths.
- User-supplied cross-domain mechanisms go into a Guide, or as Guide candidates.
- User content lacking evidence: mark “Source: user supplement; pending code/runtime validation”.
- When the user volunteers real incidents, you may write “common easy-to-miss conditions” or “pending doc-update persistence”; do not fabricate historical troubleshooting docs during doc-init.
