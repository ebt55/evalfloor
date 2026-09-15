# Floor matrix

<!-- GENERATED FILE. Do not edit by hand. Regenerate with `evalfloor report`. Every number here is computed from results/sweep.json and rulings.jsonl. -->

## Headline

**1 of 5** tasks in this sweep have at least one content-free completion that scores at or above their own majority-class baseline.

Before rulings the count was **1 of 5**. The denominator is the number of tasks that produced a scored floor in this sweep; `results/coverage.md` says what is not in it and why.

> **Preregistered negative result.** Fewer than 5 flagged tasks was fixed in advance as the threshold at which the finding is that the collection is tighter than the single known case suggested. At 1 of 5, that is the finding.

| provenance | value |
|---|---|
| `inspect_ai` | 0.3.263 |
| `inspect_evals` | 0.20.0 |
| battery fingerprint | `263b597d8f98` |
| sweep digest | `f38b0e4376f5ef27` |

## What a flag means

A flagged task is not a worthless benchmark. A loose scorer inflates a number without saying the underlying task is easy, and nothing here claims anything about the conclusions of any paper that used one of these evals.

## Per task

| task | scorer | n | majority | uniform | best content-free | score | gap | flagged |
|---|---|---|---|---|---|---|---|---|
| `inspect_evals/boolq` | `inspect_ai/pattern` | 3270 | 62.2% | 50.0% | all_labels | 37.8% | -0.243 | no |
| `inspect_evals/drop` | `inspect_ai/f1` | 9535 | 7.3% | n/a | echo | 2.3% | -0.049 | no |
| `inspect_evals/gsm8k` | `inspect_ai/match` | 1319 | 3.0% | n/a | echo | 2.1% | -0.009 | no |
| `inspect_evals/paws` | `inspect_ai/includes` | 8000 | 55.8% | 49.6% | all_labels | 100.0% | +0.442 | all_labels |
| `inspect_evals/sec_qa_v2` | `inspect_ai/choice` | 100 | 31.0% | 22.6% | format_only | 21.0% | -0.100 | no |

## Every battery member, every task

| task | scorer | empty | whitespace | refusal | all_labels | all_letters | echo | boilerplate | format_only | majority | uniform |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `inspect_evals/boolq` | `inspect_ai/pattern` | 0.0% | 0.0% | 0.0% | 37.8% | 0.0% | 0.0% | 0.0% | 0.0% | 62.2% | 50.0% |
| `inspect_evals/drop` | `inspect_ai/f1` | 0.0% | 0.0% | 0.1% | n/a | 0.0% | 2.3% | 0.2% | 0.0% | 7.3% | n/a |
| `inspect_evals/gsm8k` | `inspect_ai/match` | 0.0% | 0.0% | 0.0% | n/a | 0.0% | 2.1% | 0.0% | 0.0% | 3.0% | n/a |
| `inspect_evals/paws` | `inspect_ai/includes` | 0.0% | 0.0% | 0.0% | 100.0% | 0.0% | 12.1% | 0.0% | 0.0% | 55.8% | 49.6% |
| `inspect_evals/sec_qa_v2` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 21.0% | 31.0% | 22.6% |

## Counts, not rates

| task | scorer | member | correct | scored |
|---|---|---|---|---|
| `inspect_evals/boolq` | `inspect_ai/pattern` | empty | 0 | 3270 |
| `inspect_evals/boolq` | `inspect_ai/pattern` | whitespace | 0 | 3270 |
| `inspect_evals/boolq` | `inspect_ai/pattern` | refusal | 0 | 3270 |
| `inspect_evals/boolq` | `inspect_ai/pattern` | all_labels | 1237 | 3270 |
| `inspect_evals/boolq` | `inspect_ai/pattern` | all_letters | 0 | 3270 |
| `inspect_evals/boolq` | `inspect_ai/pattern` | echo | 0 | 3270 |
| `inspect_evals/boolq` | `inspect_ai/pattern` | boilerplate | 0 | 3270 |
| `inspect_evals/boolq` | `inspect_ai/pattern` | format_only | 0 | 3270 |
| `inspect_evals/boolq` | `inspect_ai/pattern` | majority | 2033 | 3270 |
| `inspect_evals/boolq` | `inspect_ai/pattern` | uniform | 8173 | 16350 |
| `inspect_evals/drop` | `inspect_ai/f1` | empty | 0 | 9535 |
| `inspect_evals/drop` | `inspect_ai/f1` | whitespace | 0 | 9535 |
| `inspect_evals/drop` | `inspect_ai/f1` | refusal | 0 | 9535 |
| `inspect_evals/drop` | `inspect_ai/f1` | all_letters | 0 | 9535 |
| `inspect_evals/drop` | `inspect_ai/f1` | echo | 0 | 9535 |
| `inspect_evals/drop` | `inspect_ai/f1` | boilerplate | 0 | 9535 |
| `inspect_evals/drop` | `inspect_ai/f1` | format_only | 0 | 9535 |
| `inspect_evals/drop` | `inspect_ai/f1` | majority | 689 | 9535 |
| `inspect_evals/gsm8k` | `inspect_ai/match` | empty | 0 | 1319 |
| `inspect_evals/gsm8k` | `inspect_ai/match` | whitespace | 0 | 1319 |
| `inspect_evals/gsm8k` | `inspect_ai/match` | refusal | 0 | 1319 |
| `inspect_evals/gsm8k` | `inspect_ai/match` | all_letters | 0 | 1319 |
| `inspect_evals/gsm8k` | `inspect_ai/match` | echo | 28 | 1319 |
| `inspect_evals/gsm8k` | `inspect_ai/match` | boilerplate | 0 | 1319 |
| `inspect_evals/gsm8k` | `inspect_ai/match` | format_only | 0 | 1319 |
| `inspect_evals/gsm8k` | `inspect_ai/match` | majority | 40 | 1319 |
| `inspect_evals/paws` | `inspect_ai/includes` | empty | 0 | 8000 |
| `inspect_evals/paws` | `inspect_ai/includes` | whitespace | 0 | 8000 |
| `inspect_evals/paws` | `inspect_ai/includes` | refusal | 0 | 8000 |
| `inspect_evals/paws` | `inspect_ai/includes` | all_labels | 8000 | 8000 |
| `inspect_evals/paws` | `inspect_ai/includes` | all_letters | 0 | 8000 |
| `inspect_evals/paws` | `inspect_ai/includes` | echo | 970 | 8000 |
| `inspect_evals/paws` | `inspect_ai/includes` | boilerplate | 0 | 8000 |
| `inspect_evals/paws` | `inspect_ai/includes` | format_only | 0 | 8000 |
| `inspect_evals/paws` | `inspect_ai/includes` | majority | 4464 | 8000 |
| `inspect_evals/paws` | `inspect_ai/includes` | uniform | 19829 | 40000 |
| `inspect_evals/sec_qa_v2` | `inspect_ai/choice` | empty | 0 | 100 |
| `inspect_evals/sec_qa_v2` | `inspect_ai/choice` | whitespace | 0 | 100 |
| `inspect_evals/sec_qa_v2` | `inspect_ai/choice` | refusal | 0 | 100 |
| `inspect_evals/sec_qa_v2` | `inspect_ai/choice` | all_labels | 0 | 100 |
| `inspect_evals/sec_qa_v2` | `inspect_ai/choice` | all_letters | 0 | 100 |
| `inspect_evals/sec_qa_v2` | `inspect_ai/choice` | echo | 0 | 100 |
| `inspect_evals/sec_qa_v2` | `inspect_ai/choice` | boilerplate | 0 | 100 |
| `inspect_evals/sec_qa_v2` | `inspect_ai/choice` | format_only | 21 | 100 |
| `inspect_evals/sec_qa_v2` | `inspect_ai/choice` | majority | 31 | 100 |
| `inspect_evals/sec_qa_v2` | `inspect_ai/choice` | uniform | 113 | 500 |

## The battery

| member | kind | completion |
|---|---|---|
| `empty` | content_free | the empty string |
| `whitespace` | content_free | a single newline |
| `refusal` | content_free | a short refusal sentence |
| `all_labels` | content_free | every distinct target in the dataset, concatenated |
| `all_letters` | content_free | the option letters A B C D E |
| `echo` | content_free | the sample input, echoed back verbatim |
| `boilerplate` | content_free | a long fluent paragraph containing no task content |
| `format_only` | content_free | the answer template with a placeholder |
| `majority` | reference | the modal target of the dataset |
| `uniform` | reference | a target drawn uniformly from the label set, averaged over seeds |

Literal strings, fixed by preregistration:

* `refusal` = `I'm sorry, but I can't help with that.`
* `format_only` = `ANSWER: A`
* `boilerplate` = 571 characters, beginning `Thank you for the question. This is an interesti...`
