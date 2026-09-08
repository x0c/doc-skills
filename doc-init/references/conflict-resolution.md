# Conflict Resolution

This document defines how doc-init handles conflicts with existing docs after product truth is confirmed.

## When it triggers

Whenever truth is established at any stage (product north star, Q&A, user correction) and it conflicts with docs already under `docs/` (including this session’s or earlier doc-init output, or hand-written docs, whether or not committed to git), the conflicting docs must be corrected in the same session. Do not leave two contradictory conclusions in `docs/` at the same time. Follow global rule “§5 Single source of truth”.

## Adjudication principles

Default: go back to authoritative sources (product docs / backend PRD / code), verify the original wording, then decide. Do not skip checks because an old doc “claims it already read the PRD”—that claim itself is an unverified assertion.

Only when the user has reviewed the source and explicitly judges the source/code outdated, and insists on the latest understanding, treat the user’s confirmation as authoritative.

## Anti-thrashing: persist adjudication records

When the user overrides a source, write a dated 【Ruling】 entry with rationale into the relevant KB (format in `references/document-templates.md` §6):

```
- 【Ruling】[YYYY-MM-DD] User confirmed overturning [original authoritative conclusion]: [correct conclusion for this product/domain] (reason: [why the source is outdated/inapplicable]). Future doc-init/doc-update that reads this entry must not reverse it unless the user changes their mind again; recommend syncing the source doc, but this repo must not edit across repos on its own.
```

Future doc-init/doc-update must not overturn this ruling after reading it. Also remind the user that backend source docs should be updated, but doc-init must not edit across repos on its own.

## Propagation: apply automatically after ruling—no second confirmation

Once truth is ruled, apply changes automatically:

- **Rename (canonical term):** replace across all docs; keep implementation aliases (code class names / table names unchanged)
- **Change logic:** including deleting entire KBs, removing domain-map rows, and rewriting KBs that cross-reference them—also automatic
- Afterward, list in detail what was changed/deleted; uncommitted deleted docs cannot be recovered via git, so the **deletion inventory must be complete**
