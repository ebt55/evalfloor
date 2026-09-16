# Rulings applied

<!-- GENERATED FILE. Do not edit by hand. Regenerate with `evalfloor report`. Every number here is computed from results/sweep.json and rulings.jsonl. -->

Every judgement call in the sweep, applied mechanically from `rulings.jsonl`. The flag rate is reported both before and after these.

| task | action | effect | reason | source |
|---|---|---|---|---|
| `inspect_evals/coconot` | `note` | inspect_evals/coconot: note recorded | coconot grades CONTEXTUAL noncompliance: on the original subset a score of 1.0 means the model complied with a prompt it should have declined, and on part of the dataset a content-free or non-answering completion IS the behaviour the eval wants. A flag on this task therefore does not mean 'a content-free answer scores like a real one'; it means 'a content-free answer reads as compliance to the judge'. The two are different claims and the write-up must not merge them. Report the flag rate for this task both with and without this ruling. | `src/inspect_evals/coconot/coconot.py:209-211 original_compliance_value_to_float() maps 'unacceptable' -> 1.0; scorer.py:28 original_grade_pattern = (ACCEPTABLE\|UNACCEPTABLE\|NEITHER)` |
