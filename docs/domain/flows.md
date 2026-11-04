# Main flows

## 1. Prepare a task

The operator authors a task as a pull request on a target → the system builds a task from it, with the base as the starting point and the tests of the change kept apart as the hidden oracle → the operator checks that the oracle fails on the base and passes on the reference solution → the task is frozen.

## 2. Run a batch

The operator starts a batch for one repetition → the system checks that no other run is going, that telemetry is up, that the run fits in the session and that the spend stays under the ceiling → it runs one configuration on one task, unattended, with the specification as the only input → the operator sees a one-line result per run and the next run starts.

## 3. Grade a run

A run ends → the system takes only the run's changes to a fresh environment, adds the hidden tests and runs them with the existing tests and the static analysis → it records the reward, the criteria met and the new findings → the protocol check flags any workflow step skipped without notice.

## 4. Review and confirm

A graded run is sent to the independent reviewer → the reviewer lists its findings on the run's changes → the system picks a sample of runs per configuration and task and hides which configuration produced each → the operator marks each finding as confirmed or rejected → the system reports the confirmed share per configuration.

## 5. Load, analyze and publish

The operator rebuilds the local store from the run folders and the telemetry → the system reconciles tokens and cost across its sources → the operator exports the selected runs → the system copies only the fields allowed for each target's visibility and blocks the export on any possible leak → the publication is logged.

## 6. Prepare local inference

The operator downloads the pinned model files → the system keeps a file only when its size and fingerprint match → the operator starts the server with one model → the system checks that the server refuses requests without its key → the operator measures the model's speeds and power on this machine.
