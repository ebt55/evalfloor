# eval-floor

<!-- GENERATED FILE. Do not edit by hand. Regenerate with `evalfloor report`. Every number here is computed from results/sweep.json and rulings.jsonl. -->

**What score does an answer with no content in it already get?**

## The number, and its denominator

`{flagged} of {reachable} tasks` -- **no sweep has run yet.** This line is a placeholder that `evalfloor report` fills from `results/sweep.json`. No number is claimed here until it does.

> **No preregistration is committed yet, so no sweep can produce a result.** `evalfloor sweep` refuses to write anywhere but `results/smoke/` until `PREREGISTRATION.md` is in git history, and it then stamps that commit hash here.

## What this is

A scorer in Inspect is a function of a completion and a target. It does not care whether a model produced the completion. So eval-floor drives an eval's real scorer, over its real dataset, with a battery of completions that carry no information about the sample: the empty string, a refusal, every label concatenated. No model is called. The sweep costs nothing and is deterministic, which is what makes it reproducible by anyone.

## The case that started it

Inspect Evals issue [#2331](https://github.com/UKGovernmentBEIS/inspect_evals/issues/2331) was opened on 2026-08-31 by **caiotheodoro**, who found that the constant string `"yesno"` scores 8000 of 8000 on the `paws` eval, because the eval is scored with `includes()` and both labels are substrings of that constant. **That finding is theirs, not this project's.** eval-floor generalises it, asking the same question mechanically of every task in the collection. A fix is in flight: PR [#2334](https://github.com/UKGovernmentBEIS/inspect_evals/pull/2334) by **jkopczyn** replaces the `paws` and `boolq` scorers with anchored patterns, and a maintainer comment from **MattFisher** dated 2026-09-09 calls it "merge-ready" -- but it carries no approving GitHub review, it is **not merged**, and no release contains it. `paws` in `inspect_evals` 0.20.0, the latest release, still reads `scorer=includes()`. That is why this repository pins that version: the anchor has to run against a version where the behaviour is still present. `tests/test_paws_regression.py` reproduces it from committed code.

## Reachability

The denominator comes before the result. Every declared task is either swept or excluded with a recorded reason; the full per-task table is in [`results/coverage.md`](results/coverage.md).

| reason | tasks | meaning |
|---|---|---|
| `sandbox_required` | 76 | the task or its scorer needs a container |
| `extra_dependency` | 49 | needs an optional dependency group that is not installed |
| `model_graded` | 27 | the scorer needs a grader model; not part of the deterministic arm |
| `network_required` | 17 | fetches from a URL or clones a repository at run time |
| `gated_dataset` | 7 | the Hugging Face dataset requires accepting terms or an access grant |
| `too_large` | 3 | the dataset exceeds the disk cap recorded in PREREGISTRATION.md |
| **reachable** | **58** | the deterministic sweep can run these |
| **declared total** | **237** | |

## The battery

Members are defined semantically and written down in the task's own answer template when it declares one. Both arms, `raw` and `rendered`, are scored and reported, so the effect of that rendering is visible rather than assumed. The flag rule uses the rendered arm.

| member | kind | semantics | templated | completion |
|---|---|---|---|---|
| `empty` | content_free | literal | no | the empty string |
| `whitespace` | content_free | literal | no | a single newline |
| `refusal` | content_free | literal | no | a short refusal sentence |
| `all_labels` | content_free | labels | yes | every distinct target in the dataset |
| `all_letters` | content_free | literal | no | the option letters A B C D E, bare |
| `echo` | content_free | literal | no | the sample input, echoed back verbatim |
| `boilerplate` | content_free | literal | no | a long fluent paragraph containing no task content |
| `format_only` | content_free | placeholder | yes | the answer template with a placeholder |
| `majority` | reference | label | yes | the modal target of the dataset |
| `uniform` | reference | label | yes | a target drawn uniformly from the label set, averaged over seeds |

Literal strings, fixed by preregistration:

* `refusal` = `I'm sorry, but I can't help with that.`
* `format_only` = `ANSWER: A`
* `boilerplate` = 571 characters, beginning `Thank you for the question. This is an interesti...`

> **Flag rule.** A task is flagged when at least one content-free member scores at or above that task's own `majority` baseline **and** strictly above zero. `majority` is computed per task from the dataset, never assumed: the PAWS test split is 55.8 per cent `No`, so its chance line is 0.558.

## Instrument defects found so far

Defects are logged, not quietly fixed. What the instrument got wrong is what tells a reader how far to trust what it now says. Full write-ups in [`INSTRUMENT_LESSONS.md`](INSTRUMENT_LESSONS.md).

| # | defect | what it would have invalidated |
|---|---|---|
| 001 | `choice()` tasks were not being driven at all | every multiple-choice row; 16 of the first 20 tasks use `choice()` |
| 002 | the flag rule fired on `0 >= 0` | any task the harness could not drive, turning instrument failures into findings |
| 003 | reference baselines could not parse on multiple-choice tasks | the chance line the whole flag rule rests on, on every multiple-choice task |
| 004 | a shuffled dataset made every limited sweep non-reproducible | nothing published, because the manual check happened to compare two unlimited sweeps; it would have hit the first sampled arm |
| 005 | rendering generalised, replacing the special case in 003 | no number, but it left two members written in the task's answer template and six written outside it for no reason a reader could check |
| 006 | an ungradeable grader response was about to be reported as a zero | nothing published -- it was caught on a mock -- but it is the exact shape this project exists to find: a number that looks like a measured floor and is not one |
| 007 | an eval's own grade vocabulary was being converted to zero | every graded number on the first real run, in the direction that understates the floor |
| 008 | the provider pin was requested on a channel that was overwritten | the judge-disagreement figure and the pinned cost line published in 255eb3a, both measured under routing that was never recorded |

## Limitations

| limitation | what it means for the number |
|---|---|
| A flagged task is not a worthless benchmark | a loose scorer inflates a number without saying the underlying task is easy. **No claim is made about the conclusions of any published paper** that used any of these evals. |
| One version pin | everything here is measured on `inspect_ai` 0.3.263 and `inspect_evals` 0.20.0. Rows from different versions are never mixed; on any bump the whole sweep re-runs. |
| Deterministic scorers only | model-graded tasks are excluded from this number and deferred to a separate arm with its own intervals. The exclusion is counted, not hidden. |
| The rendering rule is a choice | writing a member in the task's answer template changes what it scores. Both arms are published so the size of that effect is visible, but the headline depends on which arm is preregistered. |
| Reachability is far below the collection size | most tasks need a container, a grader model, a gated dataset or an extra dependency. The denominator is published as prominently as the rate. |
| `echo` on multimodal tasks | where inputs are images, echoing the input back is not well defined; such tasks are marked in the coverage file. |
| One judge, and it can be wrong | the graded arm is scored by a single cheap model. Its id and the snapshot served are recorded in every row, and a second grader from a different family gives a measured disagreement rate -- which bounds the judge noise rather than removing it. |
| Per-eval grade vocabularies | graded evals answer in their own words (ACCEPTABLE / NEITHER / COMPLIANCE and so on), and Inspect's generic converter silently returns 0.0 for any it does not know, which understates a floor. Mappings live in `verdict_maps.jsonl`, each quoting the eval source line; an unmapped verdict is excluded and reported, never zeroed. |

## Reproducing it

```
uv venv && uv pip install -e ".[dev]"
pytest                                 # includes the #2331 anchor
evalfloor inventory                    # regenerate the task inventory
evalfloor check inspect_evals/paws     # exits non-zero
evalfloor sweep --first-sweep --out results/
evalfloor report                       # regenerates every number here
```

Every number in `results/` and in this file is generated. None is typed by hand. Judgement calls live in `rulings.jsonl`, one row each, quoting the source line they came from, and the report applies that file mechanically. `evalfloor sweep` refuses to write a non-smoke result unless `PREREGISTRATION.md` is already committed in git history, and it records that commit hash in every file it generates.

## Disclosure

**Built with LLM coding agents (Claude), with the author reviewing every number's source.** The harness, the battery definitions and the tests were written with Claude Code doing the typing under direction. The design, the preregistration, the measurement choices and every claim made about the results are the author's, and the anchoring result is checked in as a test anyone can run against pinned versions rather than taken on trust.

## Licence

MIT, (c) 2026 Ebin Babu Thomas.
