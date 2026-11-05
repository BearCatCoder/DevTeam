# Portable workflow contract v1

These optional Python 3.9+ / Git helpers supplement the ten standalone agents.
They are **not installed** by `install.py`. Run them from this checkout, using
absolute script paths when auditing another project. No hook makes their use
automatic. DevTeam and the read-only specialists retain their original command
restrictions: an authorized local operator, or QA with a scoped approved check,
runs helpers. The documentation writer may persist supplied workflow data but
cannot run local scripts. Missing helpers require explicit manual evidence
review, not a claim of machine validation.

## P0: record and audit scope

Inspect the script before use. Keep output **outside** the audited project:

```bash
python3 scripts/workflow.py snapshot --root /path/to/project --output /tmp/task-baseline.json
python3 scripts/workflow.py audit --root /path/to/project --input /tmp/task-baseline.json --scope /path/to/scope.json --output /tmp/task-audit.json
```

`examples/scope.json` defines the v1 scope object:

| Field | Meaning |
| --- | --- |
| `allowed` | Exact repository-relative POSIX file paths, no globs or directories |
| `prohibited` | Explicitly forbidden file paths; all paths outside `allowed` are also forbidden |
| `owners` | Every allowed path maps to one exact `devteam-*` role |
| `section_review` | Paths with section restrictions that need explicit review; any change blocks the automatic audit |

Record allowed/prohibited sections in the assignment's `contracts` and serialize
all writes to that file. A whole-file hash cannot prove section compliance;
this version deliberately does not issue a section-level pass. Use a narrower
whole-file assignment only after explicit ownership agreement, or report manual
review separately without changing the blocked machine result.

Snapshots hash working files (including ignored and untracked files), modes,
and symlink targets without following symlinks; record Git HEAD, index and dirty
status; and identify the repository root. Unchanged user modifications are not
new violations. Adds, deletes, type/mode changes and Git HEAD/index drift are
audited. Unexpected changes block completion, and **nothing is reverted**.
Take a fresh baseline per serialized delegation. Do not run unrelated writers
during capture/audit. For parallel disjoint tasks, audit their union, then review
per-role tool traces: a final diff alone cannot attribute each write to an agent.

Limitations: snapshots are not atomic across a concurrently changing tree, do
not monitor outside-root writes, restored/transient writes, empty directories,
or symlink referent changes. Symlink ownership and concurrent user edits within
an allowed file require explicit review. All ignored files are included, so
large dependency trees can be costly; there is intentionally no silent exclusion
that could hide changes. Avoid secret-bearing evaluation projects.

## Optional edit-path restriction overlay

```bash
python3 scripts/isolation.py --root /path/to/project --scope /path/to/scope.json --verify
```

The command prints a configuration fragment, never edits configuration, and
with `--verify` resolves all ten installed agents under that temporary overlay.
Only the assigned owner's exact absolute paths receive edit permission. It
denies shell and the three remote-tool families for all roles, preventing their
use as alternate write channels. Thus shell-based QA is **blocked in this mode**;
an authorized operator can execute checks separately. Read-only roles remain
read-only, including when mistakenly listed as owners.

After a successful resolved check, an operator can review the printed JSON and
provide it through OpenCode's `OPENCODE_CONFIG_CONTENT` for the task process (or
carefully merge it into project configuration). The script does not start that
process or install settings. Do not use an auto-approval flag. Symlink/pattern
paths are rejected. Verify again in the actual target configuration, especially
with plugins or project overrides. Normal mode remains prompt-guided plus
post-hoc audited. This optional mode restricts **OpenCode edit-tool permissions**;
it is not an OS filesystem sandbox and does not isolate reads or defeat plugins.
Resolved checks do not prove that every runtime write tool enforces permissions.
If verification fails, report blocked and retain the portable audit fallback.

GitHub/Jira permission review: actual MCP operation catalogs are integration-
specific and none are configured by this package. The existing `github_*`,
`jira_*`, `atlassian_*` **ask** rules are retained for backward compatibility,
not changed to blanket allow or guessed operation names. Every remote write
requires explicit target/operation authorization. Sites with a known catalog
should replace broad ask rules with exact permitted operation names and deny
the remainder, then inspect resolved permissions. Shell approval also remains
operation-scoped. Review-only roles retain no local edit access.

## P1: versioned handoff schema

The normative executable v1 schema is `validate_handoff()` in
`scripts/workflow.py`; it uses the standard library, not a JSON Schema dependency.
`examples/handoff.json` is an honest blocked example, not claimed execution.
Additional role-specific fields are permitted. Unknown schema versions fail.

| Required field | Type / rules |
| --- | --- |
| `version` | Integer `1` |
| `task_id`, `summary`, `state_id` | Nonempty strings; use snapshot state ID for current evidence; unavailable state cannot support acceptance |
| `role` | One of the nine exact specialist names |
| `mode` | `analyze`, `implement`, `test`, `document` |
| `status` | `done`, `blocked`, `needs-owner`; done means assignment finished, not accepted |
| `reviewed`, `changed` | Relative path lists; changes must belong to role and approved scope |
| `scope` | Scope object above |
| `dependencies`, `contracts` | Lists of resolved prerequisites and contract/ownership decisions |
| `next_owner` | Specialist name or explicit null |
| `criteria` | Objects `{id, outcome, checks: [check IDs]}` |
| `checks` | Objects `{id, kind, command, exit_code, outcome, evidence: [reference IDs], state_id}` |
| `findings` | Objects `{severity, summary, evidence}`; severity info/low/medium/high/critical |
| `risks`, `limitations` | Lists; empty is valid only when accurate |

Outcomes: `passed`, `failed`, `blocked`, `not_run`, `inconclusive`. A passed
criterion references at least one passed check. Check kind is `self_check`,
`independent_qa`, or `review`. Only QA may report `independent_qa`. A passed
command requires exit code 0 and evidence; manual review has an empty command,
null exit code, kind `review`, and evidence. Unrun/blocked checks have null exit
codes. Every check's state ID must match its handoff. Never fabricate command
execution to satisfy this schema.

```bash
python3 scripts/workflow.py handoff --input examples/handoff.json
python3 scripts/workflow.py handoff --input /tmp/handoff.json --scope /tmp/approved-assignment.json
```

For the second form, `--scope` is the **approved assignment object**, containing
task_id, role, mode, scope, dependencies, contracts. These must match the handoff;
the first form only validates structure. Keep approvals separate from
specialist-reported data. Missing evidence causes correction or blocking.

## Completion gates

```bash
python3 scripts/workflow.py gates --input /tmp/gate-packet.json --evidence-root /tmp/task-evidence
```

A v1 gate packet has `version`, `state_id`, `criteria` (required criterion IDs),
`assignments` (task-ID -> approved assignment), `handoffs` (current final
handoffs only), `audit` (actual audit result), `blockers`, `security` and
`documentation` (each `{required: boolean, reason: string}`), and `evidence`.
`evidence` maps each reference ID to `{path: relative-artifact-path, sha256}`.
The tool verifies that referenced local artifacts exist under `--evidence-root`
and match their hashes. Without those artifacts acceptance fails closed.

It emits separate implemented, QA-verified, security-reviewed-when-applicable,
documented-when-applicable, evidence-artifacts-verified, and accepted gates.
Accepted requires all gates, clean current audit, no blockers/findings, current
done handoffs, and independent QA evidence for every requested criterion.
Resolve findings with owner fixes/review and replace current handoffs while
retaining historical evidence separately. This deliberately conservative gate
does not waive low-severity findings automatically.

Artifact hashes prove integrity, **not truth or authorship**. An authorized
operator must bind role/session, command output and audited snapshot to actual
tool traces, never populate approvals or trusted evidence solely from model
claims. The CLI does not cryptographically authenticate agents, enforce its own
invocation, or intercept Task advancement. The coordinator prompt requires that
gate results be obtained and reviewed before advancing; lack of the helper is
a disclosed manual fallback. Design/docs-only work uses its deliverable-specific
review and does not call the implementation acceptance gate.

## Durable checkpoint and reconciliation

Use for multi-step tasks only. A checkpoint object contains:

```text
version: 1
task_id: nonempty string
baseline: original snapshot object
current: last reconciled snapshot object
scope: approved scope object (includes owned files)
status: active | blocked | done
dependencies, criteria, handoffs, pending_reviews, blockers: lists
completed_mutations: stable IDs of confirmed completed operations
```

Handoffs are full validated objects, including summaries and evidence. Save the
operator-assembled object atomically and reconcile read-only:

```bash
python3 scripts/workflow.py checkpoint --root /path/to/project --input /tmp/proposed-checkpoint.json --output /tmp/checkpoint.json
python3 scripts/workflow.py resume --root /path/to/project --input /tmp/checkpoint.json --output /tmp/reconciliation.json
```

Atomic replacement flushes/fsyncs a temporary file in the destination directory
before rename; symlink outputs are refused. This is single-writer bookkeeping,
not a concurrent database or crash-proof distributed transaction. `resume` never
updates the checkpoint or repository. Any state drift—even allowed-path or
unrelated user changes—blocks automatic advancement and invalidates prior
verification conservatively. Review drift, preserve edits, rerun checks as needed,
then save a new current snapshot/checkpoint. Repeating reconciliation has no
mutation side effects. Completed mutation IDs are returned without replaying
them. Remote retries require current-state inspection and user authorization;
this tool never calls remote systems, so it cannot guarantee exactly-once remote
operations. There is no autonomous restart, scheduler, lifecycle hook, session
restoration, or automatic recovery of a killed OpenCode process.

## P2: policy maintenance

`policy/reliability-v1.md` is canonical. `python3 scripts/policy.py --write`
regenerates only marked policy blocks; `python3 scripts/policy.py` checks drift.
Tests also compare the repeated specialist collaboration policy. Installed
Markdown stays self-contained; exact resolved prompt equality remains checked
by the unchanged `scripts/validate.py`. Restart OpenCode after agent updates.
