# Coverage

<!-- GENERATED FILE. Do not edit by hand. Regenerate with `evalfloor report`. -->

This file is a placeholder carrying the shape the generator will fill. Every task
in `inspect_evals` gets exactly one row here: either it was swept, or there is a
recorded reason it could not be. The denominator of the headline number is the
count of rows with status `reachable`, and it is reported before the result.

## Exclusion reasons

| reason | meaning |
|---|---|
| `gated_dataset` | the Hugging Face dataset requires accepting terms or an access grant |
| `sandbox_required` | the task declares a sandbox (Docker image or compose file) |
| `network_required` | the task fetches from a URL or clones a repository at run time |
| `too_large` | the dataset exceeds the disk cap recorded in PREREGISTRATION.md |
| `extra_dependency` | the task needs an optional dependency group not installed |
| `model_graded` | the scorer needs a grader model; out of scope for the deterministic arm |
| `load_error` | the task function raised; the exception is recorded verbatim |

## Rows

| task | status | reason | detail |
|---|---|---|---|
| _(none yet -- no sweep has run)_ | | | |

## Totals

| | |
|---|---|
| registered tasks | _pending_ |
| reachable | _pending_ |
| excluded | _pending_ |
