# AI Track Record

> Benchmarking AI coding agents from spec to pull request: cost, time and quality across models and prompt versions.

AI Track Record is a local-first benchmark for AI coding agents. It runs the same specification-to-pull-request task under different models and prompt workflows, grades every run with hidden tests the agent never sees, and publishes cost, time and quality side by side, including every failed attempt.

**Status:** planning. There is no code yet. The first public results are planned for the first week of December 2026.

## What it measures

- **Correctness:** hidden acceptance tests derived from the specification, plus the project's existing tests.
- **Quality:** static analysis, an independent code review and, later, a calibrated mergeability verdict.
- **Cost and time:** tokens, cost and duration of every run, per model and per sub-agent.
- **Reliability and honesty:** how consistently a configuration succeeds, and how often an agent reports success while the hidden tests fail.

## What it compares

One factor at a time: the model, the model assigned to each role, the version of a prompt workflow, or the workflow itself. The first workflow under test is [relay](https://github.com/fabiombarreto/PRPs-agentic-eng), a Claude Code plugin, compared against Claude Code with no plugin.

## Documentation

Start with the [documentation index](documentation/README.md):

- [Vision and scope](documentation/product/01-vision-and-scope.md)
- [Concepts and run lifecycle](documentation/product/02-concepts.md)
- [Capabilities](documentation/product/03-capabilities.md)
- [Measurement model](documentation/product/04-measurement.md)
- [Visibility and privacy](documentation/product/05-visibility-and-privacy.md)
- [Scope, roadmap and risks](documentation/product/06-scope-and-roadmap.md)
- [Decision log](documentation/decisions/decision-log.md)

## License

[MIT](LICENSE)
