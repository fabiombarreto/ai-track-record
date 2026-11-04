# Testing — mandatory guardrail for every change

This file is a binding behavioral contract, not a reference doc. Any
agent or human who changes code in this project MUST follow the guardrail
below on EVERY change — including small, single-file, or "quick" ones,
and whether or not a relay command was used. Skipping any step silently
is a violation.

`docs/context/methodology.md` governs whether the TDD track (writing
tests first) is active. THIS file governs keeping the existing suites
green afterward. They are independent: even with `tdd: false`, the
guardrail below is always in force. This guardrail is also NOT subject to
the `docs/decision-gate.md` scope exemptions — a change that is "exempt"
from the gate still requires every step here.

## The guardrail (every code change)

1. Detect. Before finishing, state explicitly whether automated tests
   exist for the code you touched (see "Detected test suites" below) and
   which suites cover it.
2. Keep tests in sync. If your change alters behavior a test asserts,
   UPDATE that test to match the intended new behavior. Never leave a
   test asserting the old behavior. Never delete, skip, comment out, or
   weaken a test just to get a green run — that is a separate
   anti-pattern (see docs/anti-patterns.md).
3. Run. Run the suites that cover the changed code. Treat all tiers
   (unit, integration, e2e) with equal weight — at minimum run the e2e
   suite; a green unit run does not excuse an unrun e2e suite.
4. Report honestly. State which suites ran, the pass/fail result, and
   what you changed in the tests and why.

## Fallback — when you CANNOT run the tests

If for ANY reason a suite cannot run (missing dependency, no browser or
display for e2e, services not up, unknown command, timeout, sandbox or
permission limit, etc.), you MUST NOT stay silent. At the END of your
response:

1. Warn the user, in plain language, that the tests were not run.
2. Name which suite(s) could not run and the specific reason (the actual
   error or the missing precondition).
3. Give exact, copy-pasteable commands to run them manually, including
   any setup required first (install browsers, start services, set env
   vars, seed the database).

A change that touched test-covered code and ends with neither a test run
nor this explicit warning is incomplete.

## Detected test suites

No automated test suites were detected at `*init` time. The guardrail
above still applies the moment any suite is added: record its run command
and prerequisites here, then keep it green on every subsequent change. If
you believe this project should have tests (especially e2e), say so to
the user rather than proceeding silently.
