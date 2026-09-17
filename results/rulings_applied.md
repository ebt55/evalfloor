# Rulings applied

<!-- GENERATED FILE. Do not edit by hand. Regenerate with `evalfloor report`. Every number here is computed from results/sweep.json and rulings.jsonl. -->

Every judgement call in the sweep, applied mechanically from `rulings.jsonl`. The flag rate is reported both before and after these.

## Rulings that matched no task in this sweep

| task | action | reason |
|---|---|---|
| `inspect_evals/coconot` | `note` | coconot grades CONTEXTUAL noncompliance: on the original subset a score of 1.0 means the model complied with a prompt it should have declined, and on part of the dataset a content-free or non-answering completion IS the behaviour the eval wants. A flag on this task therefore does not mean 'a content-free answer scores like a real one'; it means 'a content-free answer reads as compliance to the judge'. The two are different claims and the write-up must not merge them. Report the flag rate for this task both with and without this ruling. |
