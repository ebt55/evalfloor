# Floor matrix

<!-- GENERATED FILE. Do not edit by hand. Regenerate with `evalfloor report`. Every number here is computed from results/sweep.json and rulings.jsonl. -->

## Headline

**1 of 5** tasks in this sweep have at least one content-free completion that scores at or above their own majority-class baseline.

Before rulings the count was **1 of 5**. On the raw arm -- members written plainly, ignoring each task's answer template -- it is **2 of 5**. The headline uses the rendered arm, as preregistered. `coverage.md` says what is not in this denominator.

> **Preregistered negative result.** Fewer than 5 flagged tasks was fixed in advance as the threshold at which the finding is that the collection is tighter than the single known case suggested. At 1 of 5, that is the finding.

> **No preregistration commit recorded.** This came from a smoke run, which is exempt from the ordering gate and is not a result.

| provenance | value |
|---|---|
| `inspect_ai` | 0.3.263 |
| `inspect_evals` | 0.20.0 |
| battery fingerprint | `b019ebb6ecee` |
| sweep digest | `8c3052d5329acc7f` |

## What a flag means

A flagged task is not a worthless benchmark. A loose scorer inflates a number without saying the underlying task is easy, and nothing here claims anything about the conclusions of any paper that used one of these evals.

## Per task, rendered arm

| task | scorer | template | n | majority | uniform | best content-free | score | gap | flagged |
|---|---|---|---|---|---|---|---|---|---|
| `inspect_evals/boolq` | `inspect_ai/pattern` | bare | 3270 | 62.2% | 50.0% | all_labels | 37.8% | -0.243 | no |
| `inspect_evals/drop` | `inspect_ai/f1` | bare | 9535 | 7.3% | n/a | echo | 2.3% | -0.049 | no |
| `inspect_evals/gsm8k` | `inspect_ai/match` | bare | 1319 | 3.0% | n/a | echo | 2.1% | -0.009 | no |
| `inspect_evals/paws` | `inspect_ai/includes` | bare | 8000 | 55.8% | 49.6% | all_labels | 100.0% | +0.442 | all_labels |
| `inspect_evals/sec_qa_v2` | `inspect_ai/choice` | choice | 100 | 31.0% | 22.6% | format_only | 21.0% | -0.100 | no |

## What the rendering rule changed

Every member is defined semantically and then written down in the task's own answer template when it declares one. Both forms are scored. On a task that declares no template the two arms are identical by construction, and the rows below show that rather than asserting it.

| task | template | majority raw | majority rendered | best CF raw | best CF rendered | flagged raw | flagged rendered |
|---|---|---|---|---|---|---|---|
| `inspect_evals/boolq` | bare | 62.2% | 62.2% | all_labels 37.8% | all_labels 37.8% | no | no |
| `inspect_evals/drop` | bare | 7.3% | 7.3% | echo 2.3% | echo 2.3% | no | no |
| `inspect_evals/gsm8k` | bare | 3.0% | 3.0% | echo 2.1% | echo 2.1% | no | no |
| `inspect_evals/paws` | bare | 55.8% | 55.8% | all_labels 100.0% | all_labels 100.0% | yes | yes |
| `inspect_evals/sec_qa_v2` | choice | 0.0% | 31.0% | format_only 21.0% | format_only 21.0% | yes | no |

1 of 5 tasks here declare an answer template. The two arms disagree on 1.

**Read the disagreements the right way round.** Where the raw arm flags and the rendered arm does not, that is not the raw arm being stricter. It is the raw arm reproducing instrument defect 003: a reference baseline written as a bare label cannot parse on a multiple-choice task, so its `majority` collapses towards zero and almost anything clears it. The rendered arm gives that task a real chance line to be measured against. See `INSTRUMENT_LESSONS.md`.

## Every battery member, every task -- raw arm

| task | scorer | empty | whitespace | refusal | all_labels | all_letters | echo | boilerplate | format_only | majority | uniform |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `inspect_evals/boolq` | `inspect_ai/pattern` | 0.0% | 0.0% | 0.0% | 37.8% | 0.0% | 0.0% | 0.0% | 0.0% | 62.2% | 50.0% |
| `inspect_evals/drop` | `inspect_ai/f1` | 0.0% | 0.0% | 0.1% | n/a | 0.0% | 2.3% | 0.2% | 0.0% | 7.3% | n/a |
| `inspect_evals/gsm8k` | `inspect_ai/match` | 0.0% | 0.0% | 0.0% | n/a | 0.0% | 2.1% | 0.0% | 0.0% | 3.0% | n/a |
| `inspect_evals/paws` | `inspect_ai/includes` | 0.0% | 0.0% | 0.0% | 100.0% | 0.0% | 12.1% | 0.0% | 0.0% | 55.8% | 49.6% |
| `inspect_evals/sec_qa_v2` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 21.0% | 0.0% | 0.0% |

## Every battery member, every task -- rendered arm

| task | scorer | empty | whitespace | refusal | all_labels | all_letters | echo | boilerplate | format_only | majority | uniform |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `inspect_evals/boolq` | `inspect_ai/pattern` | 0.0% | 0.0% | 0.0% | 37.8% | 0.0% | 0.0% | 0.0% | 0.0% | 62.2% | 50.0% |
| `inspect_evals/drop` | `inspect_ai/f1` | 0.0% | 0.0% | 0.1% | n/a | 0.0% | 2.3% | 0.2% | 0.0% | 7.3% | n/a |
| `inspect_evals/gsm8k` | `inspect_ai/match` | 0.0% | 0.0% | 0.0% | n/a | 0.0% | 2.1% | 0.0% | 0.0% | 3.0% | n/a |
| `inspect_evals/paws` | `inspect_ai/includes` | 0.0% | 0.0% | 0.0% | 100.0% | 0.0% | 12.1% | 0.0% | 0.0% | 55.8% | 49.6% |
| `inspect_evals/sec_qa_v2` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 21.0% | 31.0% | 22.6% |

## Counts, not rates (rendered arm)

| task | scorer | member | correct | scored | completion scored |
|---|---|---|---|---|---|
| `inspect_evals/boolq` | `inspect_ai/pattern` | empty | 0 | 3270 | `` |
| `inspect_evals/boolq` | `inspect_ai/pattern` | whitespace | 0 | 3270 | ` ` |
| `inspect_evals/boolq` | `inspect_ai/pattern` | refusal | 0 | 3270 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/boolq` | `inspect_ai/pattern` | all_labels | 1237 | 3270 | `Yes No` |
| `inspect_evals/boolq` | `inspect_ai/pattern` | all_letters | 0 | 3270 | `A B C D E` |
| `inspect_evals/boolq` | `inspect_ai/pattern` | echo | 0 | 3270 | ` Given a passage, answer the subsequent question with either` |
| `inspect_evals/boolq` | `inspect_ai/pattern` | boilerplate | 0 | 3270 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/boolq` | `inspect_ai/pattern` | format_only | 0 | 3270 | `ANSWER: A` |
| `inspect_evals/boolq` | `inspect_ai/pattern` | majority | 2033 | 3270 | `Yes` |
| `inspect_evals/boolq` | `inspect_ai/pattern` | uniform | 8173 | 16350 | `Yes` |
| `inspect_evals/drop` | `inspect_ai/f1` | empty | 0 | 9535 | `` |
| `inspect_evals/drop` | `inspect_ai/f1` | whitespace | 0 | 9535 | ` ` |
| `inspect_evals/drop` | `inspect_ai/f1` | refusal | 0 | 9535 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/drop` | `inspect_ai/f1` | all_letters | 0 | 9535 | `A B C D E` |
| `inspect_evals/drop` | `inspect_ai/f1` | echo | 0 | 9535 | `Passage:  Hoping to rebound from their fourth-quarter collap` |
| `inspect_evals/drop` | `inspect_ai/f1` | boilerplate | 0 | 9535 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/drop` | `inspect_ai/f1` | format_only | 0 | 9535 | `ANSWER: A` |
| `inspect_evals/drop` | `inspect_ai/f1` | majority | 689 | 9535 | `2` |
| `inspect_evals/gsm8k` | `inspect_ai/match` | empty | 0 | 1319 | `` |
| `inspect_evals/gsm8k` | `inspect_ai/match` | whitespace | 0 | 1319 | ` ` |
| `inspect_evals/gsm8k` | `inspect_ai/match` | refusal | 0 | 1319 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/gsm8k` | `inspect_ai/match` | all_letters | 0 | 1319 | `A B C D E` |
| `inspect_evals/gsm8k` | `inspect_ai/match` | echo | 28 | 1319 | `Pierre, Paul, and Jacques bought 12 kg of apples. Peter want` |
| `inspect_evals/gsm8k` | `inspect_ai/match` | boilerplate | 0 | 1319 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/gsm8k` | `inspect_ai/match` | format_only | 0 | 1319 | `ANSWER: A` |
| `inspect_evals/gsm8k` | `inspect_ai/match` | majority | 40 | 1319 | `5` |
| `inspect_evals/paws` | `inspect_ai/includes` | empty | 0 | 8000 | `` |
| `inspect_evals/paws` | `inspect_ai/includes` | whitespace | 0 | 8000 | ` ` |
| `inspect_evals/paws` | `inspect_ai/includes` | refusal | 0 | 8000 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/paws` | `inspect_ai/includes` | all_labels | 8000 | 8000 | `No Yes` |
| `inspect_evals/paws` | `inspect_ai/includes` | all_letters | 0 | 8000 | `A B C D E` |
| `inspect_evals/paws` | `inspect_ai/includes` | echo | 970 | 8000 | `Sentence1: This was a series of nested angular standards , s` |
| `inspect_evals/paws` | `inspect_ai/includes` | boilerplate | 0 | 8000 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/paws` | `inspect_ai/includes` | format_only | 0 | 8000 | `ANSWER: A` |
| `inspect_evals/paws` | `inspect_ai/includes` | majority | 4464 | 8000 | `No` |
| `inspect_evals/paws` | `inspect_ai/includes` | uniform | 19829 | 40000 | `Yes` |
| `inspect_evals/sec_qa_v2` | `inspect_ai/choice` | empty | 0 | 100 | `` |
| `inspect_evals/sec_qa_v2` | `inspect_ai/choice` | whitespace | 0 | 100 | ` ` |
| `inspect_evals/sec_qa_v2` | `inspect_ai/choice` | refusal | 0 | 100 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/sec_qa_v2` | `inspect_ai/choice` | all_labels | 0 | 100 | `ANSWER: B, C, A, D` |
| `inspect_evals/sec_qa_v2` | `inspect_ai/choice` | all_letters | 0 | 100 | `A B C D E` |
| `inspect_evals/sec_qa_v2` | `inspect_ai/choice` | echo | 0 | 100 | `When implementing secure application development practices, ` |
| `inspect_evals/sec_qa_v2` | `inspect_ai/choice` | boilerplate | 0 | 100 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/sec_qa_v2` | `inspect_ai/choice` | format_only | 21 | 100 | `ANSWER: A` |
| `inspect_evals/sec_qa_v2` | `inspect_ai/choice` | majority | 31 | 100 | `ANSWER: B` |
| `inspect_evals/sec_qa_v2` | `inspect_ai/choice` | uniform | 113 | 500 | `ANSWER: B` |

## The battery

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
