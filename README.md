# DevTeam for OpenCode

Invoke **`@DevTeam`** to coordinate a development team with nine domain-specific
subagents. Each specialist runs in a separate OpenCode child session and returns
a structured handoff. The coordinator assigns work, resolves dependencies, and
routes fixes to the responsible specialist.

DevTeam covers **requirements, design, development, testing, application-security
review, documentation, and requested GitHub/Jira collaboration**. It is project-,
account-, stack-, model-, and provider-agnostic.
It discovers conventions from the active repository and its applicable instructions.
No model IDs, provider configuration, project paths, or service targets are embedded.

Environment setup, systems administration, infrastructure, DevOps, CI/CD,
deployment, publishing, and release management are outside the team's scope.

## Install

Requires OpenCode with Markdown agents, Task delegation, and agent permissions.
Configuration loading is validated with OpenCode **1.19.5**. The optional installer
and validation scripts require Python **3.9+** and use only the standard library.
Runtime use requires only the ten Markdown definitions.
Optional audit, evidence, checkpoint and evaluation helpers also use Python's
standard library; repository snapshots and evaluation fixtures require Git.

Clone this repository, then run from its root:

```bash
python3 scripts/install.py --global
```

This copies `DevTeam.md` and the nine `devteam-*.md` files to
`~/.config/opencode/agents/` (or `$XDG_CONFIG_HOME/opencode/agents/`). It adds no
plugins, dependencies, provider settings, or changes to `opencode.json`.

For installation into just one existing project:

```bash
python3 scripts/install.py --project /path/to/project
```

The destination is `/path/to/project/.opencode/agents/`. You can also copy the
ten files from `.opencode/agents/` manually. Inside this repository, OpenCode
already discovers them as project-local agents.

**Quit and restart OpenCode after installing or updating agents.** Start it in
the project you want the team to work on, then use:

```text
@DevTeam Implement the requested feature, test it, and update its documentation.
```

`DevTeam` uses `mode: all`, so it can also be selected as a primary agent. The
specialists are hidden from mention autocomplete to keep the entry point simple;
they remain available to the coordinator through the Task tool.

## Team boundaries

| Specialist | Owns | Does not do |
| --- | --- | --- |
| Product owner | Scope, priorities, acceptance criteria, acceptance assessment | Technical implementation or testing |
| Architect | Technical design, interfaces, ownership map, decision content | Code changes or final QA |
| Back-end engineer | Server-side application code, APIs, services, jobs | Frontend, database artifacts, test authoring |
| Front-end engineer | Client code, UI, accessibility, client state | Backend, database artifacts, test authoring |
| Database engineer | Data models, schema/migration source, indexes, persistence | Application business logic or live database operations |
| Dev-admin | Task ledger, ownership, dependencies, handoff completeness | Host/environment administration |
| QA engineer | Test source/fixtures, test execution, independent verification | Application fixes or scope changes |
| Security reviewer | Read-only security/privacy findings and fix review | Implementing fixes or accepting risk for the user |
| Documentation writer | User/developer docs and requested durable artifacts | Code, tests, product/design decisions |

**Dev-admin means development-work administration.** It tracks the team's work;
it has no local edit access and can use `gh` for requested GitHub collaboration.

Engineers can run existing checks as development self-checks. QA owns writing
tests and independently verifying acceptance. If QA finds a backend defect, the
coordinator returns it to the backend engineer and then asks QA to recheck it.
The same owner/fix/review loop applies to security findings.

## How work proceeds

1. Identify scope and acceptance criteria.
2. Design affected components and assign ownership of actual files/sections.
3. Delegate implementation to the relevant engineers.
4. Run independent QA and relevant security review; route fixes to their owners.
5. Update affected documentation and reconcile acceptance evidence.
6. Report completed work, actual verification results, and remaining blockers.

Only relevant specialists are invoked. A focused documentation or review request
does not trigger a full feature workflow. Design-only requests stay design-only.
Independent work can run concurrently, but overlapping file edits are serialized.
Shared contracts, full-stack files, manifests, and lockfiles receive a single
owner per assignment. Handoffs carry context explicitly between child sessions.

Examples:

```text
@DevTeam Design the search feature and produce an implementation plan. Do not implement yet.

@DevTeam Fix this API regression and add regression coverage. Keep UI behavior unchanged.

@DevTeam Implement the agreed feature across the UI, API, and data model; verify it and update the docs.

@DevTeam Review authorization in this change and report actionable findings.
```

## Codebase-aware implementation

Before editing, the back-end and front-end engineers inspect the assigned
package's instructions, manifests/lockfiles, configuration, neighboring code,
and existing checks. They identify the stack and evidenced versions, architecture,
and conventions for that package, including mixed-stack monorepos. Their handoffs
include a concise codebase profile with evidence paths and unknowns, practices
applied, and justified exceptions.

Both agents prioritize applicable repository instructions, agreed contracts, and
documented project standards. Their self-contained prompts define fallback
practices adapted to the detected stack:

- **Back end:** handler/service boundaries, input validation and resource-level
  authorization, compatible API/error contracts, resource cleanup, concurrency,
  timeouts, safe retries/idempotency, and persistence-owner coordination.
- **Front end:** design-system reuse, component/state/lifecycle conventions,
  client/server rendering boundaries, accessibility, interaction states, safe API
  consumption, and evidence-based performance work.

Engineers surface conflicting or unsafe patterns and material API uncertainty
through DevTeam. They run appropriate existing package checks and report exact
results; QA retains test authoring and independent verification ownership.

## GitHub and Jira collaboration

All ten agents can interact with GitHub and Jira when requested, within their
assigned roles. Examples include reading issues and pull requests, creating or
updating work items, posting review findings or QA evidence, and maintaining
requested task status. DevTeam passes remote targets and authorized operations
to specialists and serializes updates to the same remote item.

- **GitHub:** use an already installed/authenticated `gh` CLI or configured
  GitHub MCP integration.
- **Jira:** use an already configured/authenticated Jira or Atlassian MCP
  integration. Agents discover applicable fields and workflow transitions.
- MCP tool permissions recognize `github_*`, `jira_*`, and `atlassian_*` tool
  names with `ask`. If your integration uses another prefix, add an equivalent
  permission for its actual tool names to the relevant agent definitions in
  your OpenCode configuration. These prefixes are naming conventions, not
  embedded server URLs or accounts; permission rules do not install MCP servers.
- Targets come from your request, the active repository, or integration context.
  Agents ask when ambiguous and report missing authentication/tools as blockers.
  No account, organization, repository, Jira site/project, or credential is bundled.

For example:

```text
@DevTeam Review the GitHub PR at <PR URL> and post the security findings there.
@DevTeam Read <Jira issue URL>, implement its acceptance criteria, and add QA evidence as a comment.
@DevTeam Create Jira work items in <project URL> for the agreed implementation plan.
```

Collaboration actions may prompt for tool approval. The user request and role
still determine scope. This support covers development collaboration; commits,
pushes, merges, releases, deployment, and account/repository administration remain
outside the team's scope. Completion reports include confirmed URLs/issue keys.

## Isolation and permissions

OpenCode enforces these tool/delegation restrictions:

- The coordinator cannot edit; it can delegate only to
  the nine named specialists.
- Specialists cannot delegate to each other, back to DevTeam, or to generic agents.
- Product owner, architect, dev-admin, and security reviewer have no local edit access.
- The coordinator, these four specialists, and documentation writer have shell
  access only for `gh *` commands, with approval (`ask`).
- The documentation writer has local edit access for its assigned documents.
- Implementation and QA agents have edit access and `bash: ask` for local checks.
  A command may require approval; denied commands must be reported as blocked.
- GitHub/Jira/Atlassian MCP tool prefixes have `ask` permissions; other tools
  remain denied unless explicitly enabled.

**Domain/file ownership is an instruction-level contract, not a filesystem
sandbox.** Separate sessions share the same checkout. Since this package does
not assume a repository layout, edit-enabled agents do not have a universal
path allowlist. Their prompts require exact task-specific write scopes and
return cross-domain needs to the coordinator. Shell approval is not a sandbox
either. Strict filesystem isolation requires project-specific path permissions
or an external sandbox. Project overrides and plugins can change effective
permissions; check the resolved configuration in the project where you use it.

No specialist assumes a particular model's capabilities. If required tools or
local test prerequisites are unavailable, it reports the limitation instead
of substituting another role or claiming verification succeeded.

## Validate and maintain

### Reliability and behavioral evaluation

The ten roles and their permissions are preserved. New self-contained policy
blocks require precise ownership packets, contract-first cross-component work,
honest evidence gates and safe interruption reconciliation. See
[workflow contract v1](docs/workflow-v1.md) for executable scope audits,
validated JSON handoffs, completion gates, optional checkpoints, and the optional
resolved edit-path restriction overlay. These helpers are optional companion
tools, not automatically installed or enforced by a lifecycle hook.

The [behavioral evaluation suite](evals/README.md) has 18 fixed scenarios,
disposable fixtures, raw delegation/tool traces, write audits, manual review
criteria, and baseline/candidate comparison. Live model calls are opt-in and
may incur provider charges:

```bash
python3 evals/run.py --output /tmp/devteam-eval-offline
python3 evals/run.py --live --scenario backend-fix --model provider/existing-model --output /tmp/devteam-eval-live
```

The first command honestly records **not_run**, not passing behavioral tests.
Distinguish **static/resolved configuration checks**, **offline deterministic
tests** of helpers and simulated traces, and **real model-backed behavior**.
Even a live run stays inconclusive until its trace and scenario criteria are
reviewed. No live baseline or efficiency improvement is claimed without runs.
See [implementation verification record](docs/verification.md) for actual
commands, results and unverified behavior.

From this repository:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/validate.py
python3 scripts/policy.py
```

The first command tests installation, idempotence, collision preflight, explicit
updates, symlink handling, and offline audit/evidence/recovery invariants. The
second asks OpenCode to resolve all ten agents
and checks modes, visibility, exact prompts, model neutrality, edit/shell access,
GitHub/Jira collaboration permissions, and allowed/denied delegation. It makes
no model calls or authenticated GitHub/Jira requests and does not prove
end-to-end model behavior.
The third checks generated policy consistency. Canonical policy changes go in
`policy/reliability-v1.md`; run `python3 scripts/policy.py --write` and review the
ten generated blocks. Installed agents remain self-contained Markdown files.

To inspect installation from a target project, run:

```bash
opencode agent list
opencode debug agent DevTeam
```

After reviewing an update, install with `--replace` to replace differing files
with the same names. Identical files are left alone; conflicts abort copying
before any definitions are changed. Unrelated agents and configuration are
preserved. Global and local definitions with the same names can override each
other, so keep one intended installation per scope.

To uninstall, remove only `DevTeam.md` and the nine `devteam-*.md` files supplied
by this repository from your chosen installation directory, then restart OpenCode.

## Repository layout

```text
.opencode/agents/    Coordinator and nine self-contained specialist definitions
scripts/install.py  Global or project-local installer
scripts/validate.py Resolved OpenCode configuration checks
tests/              Installer regression checks
scripts/workflow.py Scope audit, handoff/gate validation, checkpoint reconciliation
scripts/isolation.py Optional exact edit-path overlay and resolved checks
scripts/policy.py   Canonical policy generation/drift check
policy/             Versioned source embedded into all ten prompts
evals/              Fixed behavioral scenarios, opt-in live runner and review
examples/           Versioned scope and handoff examples
docs/               Workflow contract and verification record
```
