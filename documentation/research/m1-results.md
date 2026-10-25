# M1 results: Target A tasks

> **Status:** Complete · **Last updated:** 2026-10-25 · **Owner:** Fabio Martins Barreto

This report records how milestone M1 was met: Target A's scaffold, three backend tasks with frozen specifications and base commits, and their validated hidden oracles ([schedule](../product/06-scope-and-roadmap.md#4-schedule-to-the-mvp)). Target A is a private B2B SaaS built with Django and Next.js ([D-013](../decisions/decision-log.md#d-013)). Nothing about its product, domain, code or specifications appears here.

M1 was reached on 2026-10-25, 23 days before its target date.

## Where the private material lives

Everything specific to Target A stays in the operator's WSL workspace, outside this repository:

- a local clone of Target A's repository with no remote, holding the scaffold, the tasks' base and solution tags, and the specifications;
- the task manifests and the Target A templates for the agent and verifier images;
- the built Harbor tasks.

Nothing of Target A was pushed anywhere. The repository changes from M1 are generic: the task builder, the grader and this documentation.

## Scaffold

Target A had product documentation but no application code. Following [D-014](../decisions/decision-log.md#d-014), a minimal backend scaffold was written and frozen as the first base:

- a Django 6.1 and Django Ninja API on PostgreSQL 16, managed with uv, in a subfolder of a monorepo;
- five modules that talk only through their service layers, a development JWT issuer, and data partitioned by tenant;
- reference data loaded by an idempotent command from data files that Target A's documentation already validated;
- 48 tests through the HTTP API, passing with deprecation warnings treated as errors.

The scaffold follows Target A's own documented stack and coding standards, and stays as small as the three tasks allow. Infrastructure that the tasks do not need, such as queues, object storage and the frontend, is left out.

## Tasks

The three tasks form a series of pull requests. Each base commit holds the previous task's reference solution, as if that pull request had been merged. Relay's context documentation was generated at the first base with the context builder (`*init`) and refreshed at each later base (`*update`). It always describes only the code at that base, never the task's feature.

Each specification was written and approved by the operator with `/relay:relay-prd`, in an interactive session outside the measured runs ([D-014](../decisions/decision-log.md#d-014)), and then frozen in the base commit. Each one has ten acceptance criteria, an interface contract with exact status codes and error bodies, and the order in which the API checks a request.

| Task | Difficulty | Shape of the work | Acceptance criteria | Hidden tests | Existing tests at the base | Reference change |
|---|---|---|---|---|---|---|
| 01 | Medium | A state machine over immutable versions, with per-role permissions, conflict errors and a history | 10 | 44 | 48 | 6 files, about 1,100 lines |
| 02 | Hard | A deterministic calculation with exact decimal rounding, rule tables per context and ordered warnings | 10 | 22 | 92 | 8 files, about 1,100 lines |
| 03 | Hard | A new module with cross-module links, time-bounded access grants, a filtered read-only view and an access log | 10 | 17 | 114 | 17 files, about 1,400 lines |

The line counts include the hidden tests. Task 01 of Phase 0 was easy enough that every configuration scored 1.0 ([M0 review](phase-0-results.md#m0-review)). These tasks are meant to be harder, with many exact rules per criterion, but whether they separate the configurations is only known after the M2 pilots.

Target A's relay context declares test-driven development (`tdd: true`), as the operator decided at the first base. On these tasks relay therefore runs its test-first track, which was off on the synthetic task.

## Oracle validity (TGT-04)

Each task was checked by hand and then through Harbor, as in [WP3](phase-0-results.md#wp3-synthetic-target-and-task):

| Task | Hidden tests on the base | Existing tests on the base | All tests on the solution | `oracle` | `nop` |
|---|---|---|---|---|---|
| 01 | 44 of 44 fail | 48 of 48 pass | 92 pass | 1.0, 10 of 10 criteria | 0.0, existing tests 1.0, empty diff |
| 02 | 22 of 22 fail | 92 of 92 pass | 114 pass | 1.0, 10 of 10 criteria | 0.0, existing tests 1.0, empty diff |
| 03 | 17 of 17 fail | 114 of 114 pass | 131 pass | 1.0, 10 of 10 criteria | 0.0, existing tests 1.0, empty diff |

The checks on the solutions ran with deprecation warnings treated as errors, at least twice each. The hidden tests are named after the criteria they check (`test_acN_...`, TGT-05). They assert response bodies, not only status codes, the lesson from WP3. They build every state through the API and the shared test fixtures, never through models the task adds, so an implementation with different internals is graded the same way.

Where a specification left a detail open, the oracle follows the reading that a correct implementation cannot get wrong, and the choice is recorded with the task:

- One criterion asked for a validation error when a request had no body. The web framework rejects an empty body with 400 before any schema runs, so the hidden test sends an empty JSON object, which gets the specified 422.
- One criterion listed a role among those that receive "not found" on another tenant's routes. The specification's explicit check order answers "forbidden" first for that role on routes it may not use. The hidden test follows the check order.

## Harness changes

The task builder and the grader gained three optional manifest keys, all generic:

- `task.project_dir`: the Python project's folder inside the repository, for monorepos. The grader installs dependencies and sets the import path there.
- `task.test_support`: files from the base, such as a `conftest.py`, copied to the grading root. The existing and the hidden tests then share the same pristine fixtures, never the agent's copy.
- `[network]`: Harbor's network allowlist for the agent and verifier phases ([D-050](../decisions/decision-log.md#d-050)).

The synthetic task builds to the same `task.toml` as before and still scores 1.0 with `oracle`. The runner's option to disable `WebSearch` and `WebFetch` remains M2 work, as planned.

## Findings

### Allowlist and side services

With a network allowlist in any phase, Harbor 0.24.0 routes every Compose service without explicit networking through its egress sidecar. The database then shares the main service's network namespace: its service name no longer resolves, and it answers on `127.0.0.1`. Adding the service name to the allowlist does not help. Target A's templates point the API at `127.0.0.1`. A throwaway smoke task confirmed the D-050 allowlist end to end:

| Destination | Result |
|---|---|
| The database | Reached |
| The package index | Reached (HTTP 200) |
| Any other site | Blocked |
| `oracle` and `nop` | 1.0 and 0.0 |

### Clock jumps and token validation

During task 02's validation, one test got 401 midway through a sequence of calls that used the same token. The WSL clock had jumped back, as recorded in Phase 0 ([clock jumps](phase-0-results.md#clock-jumps)), and the JWT library rejected the token because its issue time was in the future. Left in place, this would make the oracle flaky and disturb the tests that agents run, for reasons unrelated to the task.

The fix was a five-minute clock-skew tolerance on token validation. It went into a commit right after the scaffold, so task 01 was rebuilt and validated again. Lesson for future targets: time-sensitive code in a scaffold needs tolerance for clock skew.

## Carried into M2

- Pilot runs on Target A's tasks, which check both difficulty and cost against the [budget projection](phase-0-results.md#cost-projection-for-the-mvp). The reference changes are several times the size of the synthetic task's.
- Disabling `WebSearch` and `WebFetch` in every configuration ([D-050](../decisions/decision-log.md#d-050)).
- The M0 follow-ups already scheduled for M2: the skipped-step flag ([D-051](../decisions/decision-log.md#d-051)) and the Phase 0 harness fixes.
