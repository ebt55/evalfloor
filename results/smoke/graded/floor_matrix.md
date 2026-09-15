# Floor matrix

<!-- GENERATED FILE. Do not edit by hand. Regenerate with `evalfloor report`. Every number here is computed from results/sweep.json and rulings.jsonl. -->

## Headline

No task produced a scored floor. There is no headline number.

> **No preregistration commit recorded.** This came from a smoke run, which is exempt from the ordering gate and is not a result.

| provenance | value |
|---|---|
| `inspect_ai` | 0.3.263 |
| `inspect_evals` | 0.20.0 |
| battery fingerprint | `b019ebb6ecee` |
| sweep digest | `d6fb7323900d0072` |

## What a flag means

A flagged task is not a worthless benchmark. A loose scorer inflates a number without saying the underlying task is easy, and nothing here claims anything about the conclusions of any paper that used one of these evals.

## Per task, rendered arm

| task | scorer | template | n | majority | uniform | best content-free | score | gap | flagged |
|---|---|---|---|---|---|---|---|---|---|
| `inspect_evals/coconot` | `inspect_ai/model_graded_qa` | bare | 10 | 0.0% | 0.0% | empty | 0.0% | +0.000 | no |

## What the rendering rule changed

Every member is defined semantically and then written down in the task's own answer template when it declares one. Both forms are scored. On a task that declares no template the two arms are identical by construction, and the rows below show that rather than asserting it.

| task | template | majority raw | majority rendered | best CF raw | best CF rendered | flagged raw | flagged rendered |
|---|---|---|---|---|---|---|---|
| `inspect_evals/coconot` | bare | 0.0% | 0.0% | - 0.0% | empty 0.0% | no | no |

0 of 1 tasks here declare an answer template. The two arms disagree on 0.

## Every battery member, every task -- raw arm

| task | scorer | empty | whitespace | refusal | all_labels | all_letters | echo | boilerplate | format_only | majority | uniform |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `inspect_evals/coconot` | `inspect_ai/model_graded_qa` | - | - | - | - | - | - | - | - | - | - |

## Every battery member, every task -- rendered arm

| task | scorer | empty | whitespace | refusal | all_labels | all_letters | echo | boilerplate | format_only | majority | uniform |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `inspect_evals/coconot` | `inspect_ai/model_graded_qa` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |

## Counts, not rates (rendered arm)

| task | scorer | member | correct | scored | completion scored |
|---|---|---|---|---|---|
| `inspect_evals/coconot` | `inspect_ai/model_graded_qa` | empty | 0 | 0 | `` |
| `inspect_evals/coconot` | `inspect_ai/model_graded_qa` | whitespace | 0 | 0 | ` ` |
| `inspect_evals/coconot` | `inspect_ai/model_graded_qa` | refusal | 0 | 0 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/coconot` | `inspect_ai/model_graded_qa` | all_labels | 0 | 0 | `` |
| `inspect_evals/coconot` | `inspect_ai/model_graded_qa` | all_letters | 0 | 0 | `A B C D E` |
| `inspect_evals/coconot` | `inspect_ai/model_graded_qa` | echo | 0 | 0 | `Can you listen to this piece of music for me and describe wh` |
| `inspect_evals/coconot` | `inspect_ai/model_graded_qa` | boilerplate | 0 | 0 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/coconot` | `inspect_ai/model_graded_qa` | format_only | 0 | 0 | `ANSWER: A` |
| `inspect_evals/coconot` | `inspect_ai/model_graded_qa` | majority | 0 | 0 | `` |
| `inspect_evals/coconot` | `inspect_ai/model_graded_qa` | uniform | 0 | 0 | `` |

## The model-graded arm

Rates here are over a **capped sample**, graded by a model, not over a whole dataset by a pure function. They are reported as Wilson 95% intervals, and the flag rule on this arm uses the interval's **lower bound** rather than the point estimate: a task is flagged only when its floor clears chance even at the pessimistic end. These numbers are never added to the deterministic arm's to make a combined rate.

| grader | value |
|---|---|
| model | `mockllm/model` |
| family | mock |
| cap | 10 samples per task per member |
| price source | no provider is called |
| API keys present | ANTHROPIC_API_KEY=no, OPENAI_API_KEY=no, OPENROUTER_API_KEY=no |
| estimated cost of this run | $0.0000 |
| grading calls made | 140 |
| cache hits / misses | 0 / 140 |

> **This run used `mockllm/model`, which is not a grader.** No provider was called and no API key was present. The numbers below exercise the plumbing and say **nothing whatever** about any eval. They are published only so the harness can be checked before money is spent running it.

### Per task

| task | scorer | n | grader | majority | best content-free | 95% CI | refusals | flagged |
|---|---|---|---|---|---|---|---|---|
| `inspect_evals/coconot` | `inspect_ai/model_graded_qa` | 10 | `mockllm/model` | NO RESULT | NO RESULT | - | 0 | not measured |

> **1 task(s) produced NO RESULT**: not one grading call succeeded, so there is no floor to report. This is written as `NO RESULT`, never as 0.0%. A task where nothing scored has not been measured, and printing a zero there would be the same class of mistake this project exists to find.

| task | errors | ungradeable | first error | grader injected via |
|---|---|---|---|---|
| `inspect_evals/coconot` | 0 | 140 | not recorded | grader |

> **140 grading calls came back ungradeable**: the grader answered, but emitted nothing that parses as a grade. That is neither a score nor an error nor a refusal, and it is **not** counted as a zero -- coercing it to zero would report a floor that was never measured. Ungradeable calls are excluded from the denominator and counted here.

### Every member, with intervals

| task | member | score | 95% CI | correct | scored | refused | ungradeable | completion |
|---|---|---|---|---|---|---|---|---|
| `inspect_evals/coconot` | empty | NO RESULT | [0.0, 0.0] | 0 | 0 | 0 | 10 | `` |
| `inspect_evals/coconot` | whitespace | NO RESULT | [0.0, 0.0] | 0 | 0 | 0 | 10 | ` ` |
| `inspect_evals/coconot` | refusal | NO RESULT | [0.0, 0.0] | 0 | 0 | 0 | 10 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/coconot` | all_labels | NO RESULT | [0.0, 0.0] | 0 | 0 | 0 | 10 | `` |
| `inspect_evals/coconot` | all_letters | NO RESULT | [0.0, 0.0] | 0 | 0 | 0 | 10 | `A B C D E` |
| `inspect_evals/coconot` | echo | NO RESULT | [0.0, 0.0] | 0 | 0 | 0 | 10 | `Can you listen to this piece of music fo` |
| `inspect_evals/coconot` | boilerplate | NO RESULT | [0.0, 0.0] | 0 | 0 | 0 | 10 | `Thank you for the question. This is an i` |
| `inspect_evals/coconot` | format_only | NO RESULT | [0.0, 0.0] | 0 | 0 | 0 | 10 | `ANSWER: A` |
| `inspect_evals/coconot` | majority | NO RESULT | [0.0, 0.0] | 0 | 0 | 0 | 10 | `` |
| `inspect_evals/coconot` | uniform | NO RESULT | [0.0, 0.0] | 0 | 0 | 0 | 50 | `` |

### Refusals

**0** grading calls were declined by the grader or the provider. Each is recorded verbatim in `refusals.jsonl` with a SHA-256 of the prompt that produced it, and counted in the tables above. None was reworded, and none was retried more than once with the identical request. A refusal is not scored as a zero: it is taken out of the denominator and reported separately, because counting a declined grading as a failed answer would quietly credit the battery member it was grading.


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
