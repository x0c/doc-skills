# Compression playbook

## Compression philosophy

**The intended reader is an AI coding agent**—not a human engineer, project manager, or tech lead. That defines what counts as “changing an action”:

- Agents route to code via **precise identifiers** (class, method, table, field, config key); narrative descriptions do not route
- Agents verify via **executable commands** (curl, SQL, build, test); “please check carefully” does not verify
- Agents locate information via **structured entry points** (table rows, index entries, § anchors); paragraph prose does not locate well

So compression is not only “delete redundancy”—it also includes **form conversion**:

| Original form | Compressed form | Why |
|---------------|-----------------|-----|
| Narrative paragraphs describing call relationships | `A.method() → B.method() → C.method()` call chain | Agent can jump directly |
| Natural-language table structure | one-line `table.field(type): meaning` | Agent can write SQL directly |
| “Important logic on line X” | `ClassName.targetMethod()` method-name anchor | Line numbers drift |
| Long paragraph explaining a config | `config.key = value // effect` one-line comment | Reading the config is enough |

---

## Core criterion

**Would this sentence change the reader’s action or judgment? If not, delete it.**

Refined for an agent reader—three sub-criteria:

1. **Routing:** Does this help the agent locate the right file/class/method? Yes → keep (prefer structured); no → next
2. **Decision:** Does this change whether the agent picks plan A or plan B? Yes → keep as a rule/constraint; no → next
3. **Verification:** Does this help the agent confirm a change is correct? Yes → keep as an executable verification command; no → deletable

None of the three hit = safe to delete.

### Delete (behavior unchanged)

| Type | Examples |
|------|----------|
| Cross-refs | “See also §X.Y” when §X.Y is immediately below |
| Restatement | Repeating the title / frontmatter / something already said above |
| Duplicate reminders | Same discipline in many places → keep the fullest one, delete the rest |
| Dead motivation | Background that does not change judgment, politeness, “it is worth noting that” |
| Historical narrative | “Formerly called X,” “deprecated” → belongs in git log |
| Empty placeholders | “None yet,” empty TODO, “to be filled” |
| Line-number refs | “Line N” / “第 N 行” → replace with `ClassName.method()` anchors, then drop the line number |
| Narrative agents do not consume | “This module is responsible for…,” “The system’s core capability is…,” “The design idea for this feature is…” — product-brochure prose has no guidance value for code changes; agents need entry points and constraints |

### Keep (changes action / judgment; deleting would distort)

- Numbers / thresholds, identifiers (class / field / API / enum / config key)
- Boundary conditions, exceptions, invariants, safety constraints, external contracts
- The one motivation sentence that would flip a decision (delete it and the direction changes)
- `§2.5` physical path quick-lookup tables — direct entry for agents locating code; do not delete or compress
- `§1.5` architecture-overview mermaid — key entry for building a whole-system picture; do not delete or compress
- `§0` TOC tables — in-KB navigation entry; do not delete or compress
- Method-name anchors (e.g. `ClassName.method() → callee()`) — stable code location; do not delete
- Paired `<!-- name:begin/end -->` 🔒 managed blocks in AGENTS.md (including `managed:inherited-agents`) — preserve verbatim in Steps 4/5; do not compress or delete

### Deduplicate

Same fact in multiple places → keep the fullest one; delete others or reduce to one pointer sentence. Count as duplicate only when it is the same number / boundary / exception.

### Form conversion (compress without deleting)

Some content is valuable but inefficient in form. Do not delete—convert to a form agents consume efficiently:

| Signal | Conversion | Example |
|--------|------------|---------|
| Narrative call relationships ≥ 3 lines | One-line call chain: `A → B → C` | “Controller calls Service, Service calls Builder, Builder calls Mapper” → `XxxController.create() → XxxService.doCreate() → XxxBuilder.build() → XxxMapper.insert()` |
| Natural-language field meanings ≥ 5 lines | Convert to a table | |
| Repeated if-else explanations | Decision table `\| condition \| branch \| result \|` | |
| Multiple paragraphs on different fields of the same table | Merge into one §4 table row | |
| Same mechanism constraints scattered around | Merge into one complete rule under §6 | |

**Conversion is not rewriting:** the result must be shorter than the original and information-preserving. If conversion gets longer, leave the original.

### Volatile facts (single source of truth)

When a concrete number is scattered in many places:
- **Authoritative source doc:** keep it; confirm it is the only maintenance point
- **Other docs:** distill a conclusion that does not change when the number changes; delete the number—do not turn it into a link (more links = more coupling)
- If you find yourself rewriting many docs to “→ link to the authority,” stop immediately—that is an anti-pattern

---

## Fix anomalies on discovery (no deferral)

Anomalies found during compression are not “compression,” but this round already has full context; deferral dumps the fix cost on a future session with no context—fix on the spot. Do not defer with “hand to doc-update” or “handle next time”:

| Anomaly | Disposition |
|---------|-------------|
| Skipped/duplicated chapter numbers, duplicate subsection titles, broken table rendering (blank lines splitting tables / misaligned headers) | Fix inside the single file; if renumbering changes other section numbers, grep whole-repo refs and sync before/while fixing |
| Dangling § refs (point to missing subsections) | Re-anchor to the correct target; if no target, rewrite as self-contained prose |
| Disordered subsections | Reorder + grep whole-repo refs (external docs may cite §N.N) and sync |
| Table/class/path names that look wrong vs code | Verify against source (entity class / @TableName / directory layout / script entry): confirmed → fix now; unverifiable → mark `待核实` / pending verification and return in the report—**do not guess** |
| Cross-doc duplication not yet converged | Converge now under “volatile facts, single source”: authority keeps the full fact; others reduce to one conclusion or pointer |

Execution tiers: single-file fixes that do not affect external refs → subagent fixes directly and records in the ledger; fixes that affect external refs or need cross-shard authority judgment → return to main agent to fix now—“high risk” means “main agent checks blast radius then fixes,” not “list it and skip.”

The only allowed leave-unfixed item for the close-out report: content contradiction with no code evidence to decide (who is right is a product/design call) → ask the user. That is a safety boundary, not deferred repair.

---

## Compression intensity by document type

Compression headroom varies hugely by type; one scale for all audits misses a lot of redundancy:

| Type | Typical headroom | Audit focus |
|------|------------------|-------------|
| Troubleshooting `troubleshooting/` | **Large (often 80%+)** | Diary narrative, duplicated verification steps, worthless appendices, “summary” that rehashes root cause, “reviewer / next review” metadata |
| Ops incident docs `operations/` (`*incident*` / `*outage*` / `YYYY-MM-DD-*`) | **Large** (same scale as troubleshooting) | Same as troubleshooting; counts toward type-driven fold threshold; prefer pointer indexes; do not relocate by default |
| Design proposals `design/` | Medium (10–30%) | Long “industry background” / “motivation” padding, full write-ups of abandoned options |
| Runbooks / playbooks | **Tiny** | Almost incompressible—every curl/SQL is an execution step |
| Review ledgers | Small | Long descriptions of closed issues may shorten; open issues must not be deleted |
| Process / architecture design docs | Small–medium | Repeated “background” for the same rule; pure narrative “why we designed it this way” |

Saying “nothing compressible” about a knowledge base is a normal conclusion. Saying “nothing compressible” about a troubleshooting record needs a strong reason.

---

## Batch compact-marker script

Append markers with a script; do not hand-edit file by file:

```python
import re, glob

TAG = '<!-- 该文档整理/压缩于 2026-06-22 -->'  # replace with the real date
pattern = re.compile(r'\n*<!-- 该文档整理/压缩于 \d{4}-\d{2}-\d{2} -->\n*')

for fpath in glob.glob('docs/**/*.md', recursive=True):
    content = open(fpath, encoding='utf-8').read()
    cleaned = pattern.sub('\n', content).rstrip()
    open(fpath, 'w', encoding='utf-8').write(cleaned + '\n\n' + TAG + '\n')
```

---

## §2.5 path liveness

When doc-compact audits a KB that contains `§2.5` physical path quick-lookup, **paths must still exist**:

```bash
# For each path row in §2.5 of every KB, ls to confirm the directory exists
grep -E '^\|' docs/*_KNOWLEDGE_BASE.md | grep '§2.5' -A 999 | grep -E '^\| [^-|]' | awk -F'|' '{print $2}' | xargs -I{} sh -c 'test -d "{}" || echo "STALE: {}"'
```

- `STALE` paths: mark as dead; after confirming code moved/deleted, remove from §2.5
- Path exists but content is empty/cleared: confirm against code whether the module moved; update the path or remove the row on the spot; if you cannot verify now, mark `待核实` / pending verification and explain in the report
- Include results in the Step 6 audit report

**Do not skip verification:** §2.5 being protected does not mean its contents stay forever correct. Protection covers structure (do not delete the whole §2.5), not every possibly stale concrete path row.

---

## Line-number replacement guide

When a doc cites line numbers (e.g. “line 535,” “Line 42,” “行 N”):

1. From citation context, determine the target file path
2. `Read` that line and confirm the current method/class name
3. Replace the line-number citation with `ClassName.method()` form
4. **Do not guess replacements:** if the target file is gone or the line is out of range, change to `[stale; originally line N]` and mark for cleanup

---

## Compression ceiling and drift protection

### When to stop

Not every doc can be compressed forever. Stop when you see:

- **Already at the minimum agent-usable information:** deleting any more line forces the agent to search code before it can act in some task scenario
- **Structured content > 80%:** tables, code blocks, and index entries dominate—almost no narrative left to compress
- **Already marked as compressed:** last compact < 30 days ago and no code change → skip; report “recently compressed”
- **Runbooks/playbooks:** every line is a step → almost incompressible (see “Compression intensity by document type” above)

### Drift risk across multiple compressions

Every compression is lossy. On the second+ pass of the same doc, check:

1. **Precise identifiers generalized:** did `XxxService.handlePayment()` become “payment handling logic”?
2. **Numbers/thresholds erased:** did `timeout 30s` become “may time out”?
3. **Causal chain broken:** did `because A, must B` become only `must B` (losing why = next code change cannot tell whether B can be removed)?
4. **Verification commands still runnable:** did a real `curl ...` become “call the API to verify”?

If drift is found → restore precise information from the code source; do not keep compressing summaries of summaries.

### Drift protection for parallel subagent compression

SKILL.md Step 5 dispatches per-doc compression to multiple subagents in parallel. That amplifies the drift risks above: serial single-agent re-compression is **the same criteria understanding drifting over time**; parallel multi-subagent compression is **different criteria understandings diverging at the same time**—harder to spot, because each subagent returns a locally plausible ledger and the main agent will miss cross-shard inconsistency without cross-checking.

When the main agent merges subagent ledgers, beyond the four drift checks above, it must also run a **cross-shard consistency pass**:

1. **Same-domain criteria consistency across subagents:** when one domain is split across subagents (e.g. billing domain, 12 docs → 2 subagents), check both treated “the same class of redundancy” the same way—A deleted all “historical narrative,” B kept it as footnotes = criteria divergence. On divergence → main agent unifies the ruling and sends back for alignment.
2. **Dedup landing for facts repeated across shards:** the same number/boundary/exception may sit in docs assigned to different subagents (e.g. a threshold in a design doc under A and a KB under B). Each subagent only sees its shard and cannot pick the authority. On merge, the main agent must **cross-shard scan the same volatile fact**: grep each subagent’s post-compress output for the same number; confirm only the authority remains and others were distilled to stable conclusions. This is the hard parallel-case check of “volatile facts, single source”—serial agents rely on memory across docs; parallel runs need post-hoc main-agent grep.
3. **Protected sections not mishandled:** subagents received the protected list, but under context pressure may still delete a `§2.5` row, a `§0` TOC entry, a method-name anchor, or a 🔒 managed block. After merge, run `grep -c` checks: each KB’s `§2.5` / `§0` / `§1.5` anchor line counts should match pre-compress (protected sections may not drop rows—only STALE paths inside may change); AGENTS.md managed-block marker pairs must still exist. Fewer lines = mishandling → roll that section back.
4. **Compact markers complete:** each subagent should append `<!-- 该文档整理/压缩于 YYYY-MM-DD -->`, but parallel runs often miss. After merge, run Step 6’s `audit.py --compact-date` hard gate—`压缩缺标识=0` / missing-marker = 0 is the last parallel defense; any miss = that subagent forgot markers; close only after fixing. If most docs were skipped as “recently compressed,” the real gate is “today’s markers ∪ last-30-day markers = full set.”

**Disposition when post-check finds drift:** single-doc drift → roll that doc back to pre-compress (`git checkout`) and re-compress; cross-shard criteria divergence → main agent issues a unified ruling and sends all divergent parties to re-compress affected passages. **Do not** patch on top of compressed output—patches decouple that doc from the criteria baseline and make the next doc-compact harder to audit.
