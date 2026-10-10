# Rulings applied

<!-- GENERATED FILE. Do not edit by hand. Regenerate with `evalfloor report`. Every number here is computed from results/sweep.json and rulings.jsonl. -->

Every judgement call in the sweep, applied mechanically from `rulings.jsonl`. The flag rate is reported both before and after these.

| task | action | effect | reason | source |
|---|---|---|---|---|
| `inspect_evals/coconot` | `note` | inspect_evals/coconot: note recorded | coconot grades CONTEXTUAL noncompliance: on the original subset a score of 1.0 means the model complied with a prompt it should have declined, and on part of the dataset a content-free or non-answering completion IS the behaviour the eval wants. A flag on this task therefore does not mean 'a content-free answer scores like a real one'; it means 'a content-free answer reads as compliance to the judge'. The two are different claims and the write-up must not merge them. Report the flag rate for this task both with and without this ruling. | `src/inspect_evals/coconot/coconot.py:209-211 original_compliance_value_to_float() maps 'unacceptable' -> 1.0; scorer.py:28 original_grade_pattern = (ACCEPTABLE\|UNACCEPTABLE\|NEITHER)` |

## Rulings that matched no task in this sweep

| task | action | reason |
|---|---|---|
| `inspect_evals/bbh` | `note` | Task property, recorded after the 0.24.0 sweep; it moves no flag. Every bbh input carries its subset's few-shot examples, each ending in an ANSWER line, and the scorers read the last one, so echo answers each subset with that subset's last example label: a constant guess. It clears the dataset-wide majority (B, 1030 of 6508) because B is no answer on the six binary subsets, where echo scores 697; on the multiple-choice subsets it is below majority (990 vs 1030). It never beats a subset's own most common answer except on word_sorting, where 8 inputs list their words already sorted. Lines are inspect_evals 0.24.0 (bbh.py) and inspect_ai 0.3.263 (the two parsers). |
