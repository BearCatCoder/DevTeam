# Implementation verification record

Date: 2026-11-05. Source baseline: `6b6735d7fe9826873e4532dc4e8e38e490c050b3`.
The starting working tree was clean. The coordinator plus nine specialists,
installer safety behavior, and existing resolved-agent checks were retained.
No provider/model installation or configuration, remote mutation, commit,
push, or deployment was performed.

## Commands and observed outcomes

| Exact command | Outcome |
| --- | --- |
| `opencode --version` | **PASS**: `1.19.5` available |
| `opencode run --help` | **PASS**: inspected `--agent`, `--format json`, `--pure`, model and session options; no model invocation |
| `opencode export --help` | **PASS**: inspected session export support; no model invocation |
| `python3 -m unittest discover -s tests -v` | **PASS, final run: 23 tests**. Installer regression tests plus offline scope, evidence, recovery, policy, deterministic fixture and review tests |
| `python3 scripts/validate.py` | **PASS: all ten agents** resolved with original modes, permissions, delegation restrictions, exact updated prompts and model neutrality |
| `python3 scripts/isolation.py --root /home/bryan/Dev/DevTeam --scope examples/scope.json --verify` | **PASS**: temporary overlay resolved exact owner edit paths and denied shell/remote operation probes for all ten agents. Printed configuration only; no project/global config installed |
| `python3 scripts/policy.py --write` | Generated v1 blocks in all ten Markdown definitions |
| `python3 scripts/policy.py` | **PASS**: all ten embedded blocks match canonical v1 |
| `python3 scripts/workflow.py handoff --input examples/handoff.json` | **PASS**: example structure valid. Example task/check status remains **blocked**, not verified work |
| `python3 evals/run.py --output /tmp/opencode/devteam-eval-offline-20261105` | Command exited 0; **all 18 behavioral scenarios not_run**, metrics null. Report at `/tmp/opencode/devteam-eval-offline-20261105/report.json` |
| `git diff --check` | **PASS**: no whitespace errors in tracked diff |

Intermediate regression run: 23 tests ran with **one error** after the gate was
tightened to reject missing assignment handoffs. The old test expected a false
acceptance result instead of a validation error. Updated that expectation to
assert the missing-handoff error; the final 23-test run passed. Earlier 20-test
iteration also passed. No application validation was weakened to satisfy tests.

## What was and was not demonstrated

- **Static/resolved configuration:** tested with actual OpenCode 1.19.5, without
  model calls. This establishes loading and permission resolution, not runtime
  permission enforcement under every tool/plugin combination.
- **Offline deterministic/simulated checks:** demonstrate that unexpected file
  changes are detected without reverting them, stale state blocks reconciliation,
  handoffs cannot expand supplied approvals, unsupported check passes are
  rejected, acceptance needs independent QA plus matching evidence artifacts,
  and review cannot promote unexecuted scenarios or false automatic invariants.
- **Real model-backed multi-agent evaluations: NOT RUN.** The paid opt-in runner
  was not invoked; provider access was not probed. No model behavior, prompt
  injection resistance, live permission denial, cost, efficiency improvement,
  or end-to-end reliability is claimed. There is no measured live baseline.
- **Feature-gated overlay:** resolved configuration passed; actual denied edit
  attempts and live delegation under the overlay remain model-behavior-unverified.
- **Interruption recovery:** checkpoint/reconciliation helpers are tested.
  The evaluation resume case seeds interrupted state; killing and automatically
  restoring a real agent session is not implemented or claimed.

## Remaining limitations / deferred work

1. Execute and manually review live baseline/candidate trials with an explicitly
   selected existing model and cost budget. The runner, frozen-agent input,
   criteria, evidence retention and comparison workflow are present; results
   cannot be invented from offline tests.
2. Automatic per-role write attribution, comprehensive child usage accounting,
   and session recovery await verified runtime trace/API integration. Current
   exports and trace review provide a portable explicit fallback. The runner's
   live event/export path has not been exercised against a model.
3. No filesystem sandbox. Optional permissions restrict edit paths and disable
   shell/remote writes; normal scope is prompt-guided plus post-hoc audited.
   Outside-root/transient writes and same-file user-edit preservation require
   stronger isolation or explicit review. Section-restricted changes block
   machine audit pending manual review.
4. Helpers are optional and coordinator use is prompt-required, not intercepted
   by a mandatory lifecycle hook. Evidence hashes establish artifact integrity,
   not truthful model authorship; approved assignments and trusted tool logs
   must come from an independent operator/reviewer.
5. Broad remote **ask** rules were reviewed and retained because this package
   has no configured MCP operation catalog. Exact-operation narrowing is
   integration-specific; remote writes still require target/operation approval.
6. No autonomous continuation, durable process sessions, exactly-once remote
   mutation guarantee, or concurrent checkpoint writers. Local reconciliation
   is read-only and repeatable; saving checkpoints is atomic single-writer
   bookkeeping.

Restart OpenCode after installing or updating the agent definitions. Running
sessions keep their previously loaded prompts.

## Update round 2 (2026-11-05, baseline `162ebac`)

Changes are uncommitted in the working tree for review. Tasks 1-9, 11, and 12
were implemented; Task 10 (enforcement plugin) was **deferred by user decision**,
so the contract remains prompt-required and not intercepted by a lifecycle hook.

After every task, all three required commands passed before the next task:
`python3 -m unittest discover -s tests`, `python3 scripts/validate.py`,
`python3 scripts/policy.py`. Intermediate failures, and how each was resolved
without weakening a check:

- Task 3: the new per-role test matched "gates" inside "delegates", and the
  "no hand-written GitHub/Jira copy" test matched legitimate coordinator
  routing text. Both matchers were narrowed to what they meant to check (word
  boundary; the removed paragraph's wording).
- Task 5: the new no-asking test matched my own policy sentence "You cannot ask
  the user questions"; the policy was reworded, the test kept.
- Task 1: existing tests and `examples/handoff.json` used free-form state ids
  (`current`, `unavailable-example-only`) that the new format rejects; they now
  use valid ids (`head:abc1234;dirty:unknown`, `none`).

Final results:

| Command | Outcome |
| --- | --- |
| `python3 -m unittest discover -s tests` | **PASS, 31 tests** |
| `python3 scripts/validate.py` | **PASS, all ten agents**, including new git/gh denies for every agent and `question` limited to DevTeam |
| `python3 scripts/policy.py` | **PASS** |
| `python3 scripts/isolation.py --root . --scope examples/scope.json --verify` | **PASS** (overlay still resolves with the new bash rule objects) |
| `python3 scripts/workflow.py handoff --input <done architect analyze handoff>` | **PASS**: a read-only role can now return `done` |
| `python3 evals/run.py --budget-usd 1 --output /tmp/opencode/devteam-eval-offline-final` | 18 scenarios **not_run**; no model calls |
| `npm view opencode-ai@1.19.5 version` | `1.19.5` exists (CI install target) |
| Python 3.9 compatibility | **Static only**: every `.py` file parses with the 3.9 grammar (`ast.parse(..., feature_version=(3, 9))`). No 3.9 interpreter was available and none was installed; CI's 3.9 job is the first real run |
| `.github/workflows/ci.yml` | YAML parses; **not run on GitHub** (nothing pushed) |
| `git diff --check` | **PASS** |

Prompt size (`wc -w`): DevTeam 1,956 -> 1,397; specialists 907-1,477 -> 438-649;
total 11,659 -> 6,434. "do not / never / cannot" occurrences: 168 -> 109.

Not demonstrated: any live model behavior, including whether shorter prompts,
work tiers, the needs-owner rule, or engineer-authored unit tests change
outcomes. Live evaluations remain not run.

Known limitations introduced or kept this round:

- `head:<sha>;dirty:unknown` identifies the commit, not uncommitted changes.
- Permission denies match command prefixes only; rewritten forms such as
  `git -C dir push` or `sh -c` are still stopped only by the prompts.
- Budget enforcement checks between scenarios, so one scenario can overshoot.
  It fails closed when a run reports no cost.

## Update round 3 (2026-11-05, baseline `7ae3fd9`)

Changes are uncommitted in the working tree for review. All six tasks were
implemented. After every task, all three required commands passed before the
next task: `python3 -m unittest discover -s tests`, `python3 scripts/validate.py`,
`python3 scripts/policy.py`. None of them failed in this round. Issues found
along the way, and how each was resolved without weakening a check:

- Task 1: moving the JSON-handoff paragraph to the `specialists` audience
  changed the source order of `all` sections, so the section word-limit test's
  ordered limits were remapped to the new structure (all: 70, 60; specialists:
  90, 40; writers: 90). Every section still has a limit.
- Task 2: the new permission rules added frontmatter words (+27 per read-only
  specialist, +9 per runner), pushing back-end (658) and front-end (653) over
  the 650 test cap and growing every file. Each file was offset in its own body,
  mainly by replacing the closing "Return task/role, status..." sentence, which
  duplicated the generated JSON key list, with a one-line pointer to the JSON
  fields its role-specific content belongs in.
- Task 2: four read-only bodies still said "run commands except requested
  GitHub `gh` operations", which contradicted the new git access; reworded to
  "beyond read-only git and requested `gh`" within the same offsets.
- Task 2: the documentation writer edits files but has `bash: "*": deny`, not
  `"*": ask`, and is not in the plan's read-only list. Its shell access was left
  unchanged, and `validate.py` asserts git inspection resolves to `deny` for it.
- Task 3: beyond `npm audit fix`, the fixer forms `pnpm audit --fix`,
  `pip-audit --fix`, and `cargo audit fix` also modify the project; they are
  denied for the reviewer and asserted in `validate.py`. Body rewritten to
  absorb the new bullet and rules (577 -> 497 words).

Final results:

| Command | Outcome |
| --- | --- |
| `python3 -m unittest discover -s tests` | **PASS, 33 tests** (new: coordinator has no JSON-handoff instruction and all nine specialists do; coordinator prose wraps at 80) |
| `python3 scripts/validate.py` | **PASS, all ten agents**. New assertions: read-only git `allow` (coordinator, four read-only roles) / `ask` (runners) / `deny` (writer); `git diff --output=x`, `git log -o x`, `git show --output x HEAD` denied for all; other git verbs and `git -C x status` not allowed; reviewer audits `ask`, fixers `deny`; `npm audit` etc. `deny` for other read-only roles and `ask` for runners |
| `opencode debug agent DevTeam` | Resolved bash order confirmed: `"*": deny`, git allows, `--output`/`-o` denies, `gh *` ask, `gh` denies |
| `python3 scripts/isolation.py --root . --scope examples/scope.json --verify` | **PASS** (overlay `bash: deny` still wins over the new rules) |
| `python3 scripts/workflow.py handoff --input <done architect analyze handoff>` | **PASS** |
| Task 4 rewrap | Script asserted the whitespace-split word sequence of `DevTeam.md` is unchanged; `validate.py` confirms loaded prompt equals source |
| `git diff --check` | **PASS** |

Prompt size (`wc -w`), round 2 -> round 3: DevTeam 1,397 -> 1,371; architect
497 -> 495; back-end 649 -> 645; database 631 -> 624; dev-admin 481 -> 478;
documentation writer 559 -> 559; front-end 644 -> 643; product owner
438 -> 437; QA 640 -> 629; security reviewer 498 -> 497. No file grew. Total
6,434 -> 6,378. "do not / never / cannot": 109 -> 105.

### Task 6: CI for `7ae3fd9`

Run [42076006561](https://github.com/BearCatCoder/DevTeam/actions/runs/42076006561):

- **Python 3.12 (ubuntu-latest): PASS.** OpenCode 1.19.5 installed from npm
  (not skipped); 31 tests passed; policy drift check passed; `validate.py`
  passed ("All 10 agents validated"). This is the first real CI run of the
  resolved-agent validation.
- **Python 3.9: FAILED in `actions/setup-python`, before any repository code
  ran.** Error: "The version '3.9' with architecture 'x64' was not found for
  Ubuntu 26.04." This is a runner-image gap, not a code incompatibility: no
  union types, `match`, parenthesized context managers, or `dict | dict`
  exist (all files still parse with the 3.9 grammar). The `versions-manifest.json`
  lists Python 3.9.25 for Ubuntu 22.04 and 24.04 only, so the 3.9 job now runs
  on `ubuntu-24.04`; 3.12 stays on `ubuntu-latest`.
- Also noted: the run warns that `actions/checkout@v4` and
  `actions/setup-python@v5` target deprecated Node.js 20. Not changed.

Python 3.9 has therefore **still never executed** this code; the modified
workflow has not run (nothing pushed).

### Not demonstrated

- Any live model behavior: whether the coordinator now answers in prose,
  actually runs the git baseline/compare, or whether the reviewer runs audits.
- The validator's matcher emulates OpenCode wildcard matching with
  `fnmatchcase` over the rules the real CLI resolves; it is not OpenCode's own
  matcher evaluating each command.
- Read-only git is pattern-scoped, not sandboxed. Unverified gaps: abbreviated
  long options (git accepts unambiguous prefixes of `--output`), and repository-
  local config such as `core.fsmonitor`, external diff drivers, or textconv
  that can run programs during `git status`/`git diff`. Cloned repositories do
  not carry `.git/config`, so these require local configuration.
- The coordinator's git baseline sees changed paths and tracked line counts,
  not further edits inside an already-untracked file or count-preserving edits
  to a dirty file.
- Dependency audits contact package registries and need the tool already
  installed; runners still resolve `npm audit fix` to `ask`, not `deny`.
