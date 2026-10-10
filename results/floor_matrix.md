# Floor matrix

<!-- GENERATED FILE. Do not edit by hand. Regenerate with `evalfloor report`. Every number here is computed from results/sweep.json and rulings.jsonl. -->

## Headline

**11 of 45** tasks in this sweep have at least one content-free completion that scores at or above their own majority-class baseline.

Before rulings the count was **11 of 45**. On the raw arm -- members written plainly, ignoring each task's answer template -- it is **33 of 45**. The headline uses the rendered arm, as preregistered. `coverage.md` says what is not in this denominator.

Of those 11, **10 rest on the template collision**: the only flagging member is `format_only` and the string it was scored on is the string `majority` was scored on, so the flag is a tie between a member and itself. Preregistration section 8.5 keeps the tie rule and requires the flag to be marked rather than silently counted; the marked rows carry **yes** in the `collision` column below.

Preregistration `PREREGISTRATION.md` was committed at `912345f8d5be` **before** this sweep ran. Anyone can check that independently: `git log --format='%H %ad' -- PREREGISTRATION.md`.

Its close-out addendum, section 11, was committed at `27cdc33933db` and was on `origin/master` **before** this sweep ran; the sweep refuses to run otherwise. The first hash this prints is that commit: `git log -S'## 11. Close-out addendum' --reverse --format='%H %ad' -- PREREGISTRATION.md`.

| provenance | value |
|---|---|
| `inspect_ai` | 0.3.263 |
| `inspect_evals` | 0.24.0 |
| battery fingerprint | `b019ebb6ecee` |
| run fingerprint | `e498a3949683` |
| shuffle seed | 42 |
| sweep digest | `7981d9ebdb69df63` |

## What a flag means

A flagged task is not a worthless benchmark. A loose scorer inflates a number without saying the underlying task is easy, and nothing here claims anything about the conclusions of any paper that used one of these evals.

## Per task, rendered arm

| task | scorer | template | n | majority | uniform | best content-free | score | gap | flagged | collision |
|---|---|---|---|---|---|---|---|---|---|---|
| `inspect_evals/aime2024` | `inspect_evals/aime_scorer` | bare | 30 | 6.7% | 3.3% | all_labels | 3.3% | -0.033 | no | no |
| `inspect_evals/aime2025` | `inspect_evals/aime_scorer` | bare | 30 | 3.3% | n/a | empty | 0.0% | -0.033 | no | no |
| `inspect_evals/aime2026` | `inspect_evals/aime_scorer` | bare | 30 | 3.3% | n/a | empty | 0.0% | -0.033 | no | no |
| `inspect_evals/arc_challenge` | `inspect_ai/choice` | choice | 1172 | 26.5% | 25.2% | format_only | 22.7% | -0.038 | no | no |
| `inspect_evals/arc_easy` | `inspect_ai/choice` | choice | 2376 | 26.6% | 19.8% | format_only | 25.1% | -0.016 | no | no |
| `inspect_evals/bbeh` | `inspect_evals/bbeh_scorer` | bare | 4519 | 3.9% | n/a | empty | 0.0% | -0.038 | no | no |
| `inspect_evals/bbeh_mini` | `inspect_evals/bbeh_scorer` | bare | 460 | 4.6% | n/a | empty | 0.2% | -0.043 | no | no |
| `inspect_evals/bbh` | `inspect_evals/bbh_scorer` | bare | 6509 | 15.8% | n/a | echo | 26.2% | +0.103 | echo (note) | no |
| `inspect_evals/bbq` | `inspect_ai/choice` | choice | 58492 | 33.4% | 33.3% | format_only | 33.3% | -0.001 | no | no |
| `inspect_evals/boolq` | `inspect_ai/pattern` | bare | 3270 | 62.2% | 50.0% | empty | 0.0% | -0.622 | no | no |
| `inspect_evals/chembench` | `inspect_evals/chembench_scorer` | choice | 2785 | 0.0% | n/a | empty | 0.0% | +0.000 | no | no |
| `inspect_evals/commonsense_qa` | `inspect_ai/choice` | choice | 1221 | 20.9% | 20.1% | format_only | 19.6% | -0.013 | no | no |
| `inspect_evals/drop` | `inspect_ai/f1` | bare | 9535 | 7.3% | n/a | echo | 2.3% | -0.049 | no | no |
| `inspect_evals/gsm8k` | `inspect_ai/match` | bare | 1319 | 3.0% | n/a | echo | 2.1% | -0.009 | no | no |
| `inspect_evals/hellaswag` | `inspect_ai/choice` | choice | 10042 | 25.7% | 24.7% | format_only | 25.0% | -0.007 | no | no |
| `inspect_evals/lab_bench_cloning_scenarios` | `inspect_evals/precision_choice` | choice | 33 | 27.3% | 23.6% | format_only | 15.2% | -0.121 | no | no |
| `inspect_evals/lab_bench_dbqa` | `inspect_evals/precision_choice` | choice | 520 | 23.1% | 19.0% | format_only | 23.1% | +0.000 | format_only | **yes** |
| `inspect_evals/lab_bench_figqa` | `inspect_evals/precision_choice` | choice | 181 | 19.3% | 13.8% | format_only | 18.2% | -0.011 | no | no |
| `inspect_evals/lab_bench_litqa` | `inspect_evals/precision_choice` | choice | 199 | 22.6% | 11.0% | format_only | 22.6% | +0.000 | format_only | **yes** |
| `inspect_evals/lab_bench_protocolqa` | `inspect_evals/precision_choice` | choice | 108 | 26.9% | 15.9% | format_only | 17.6% | -0.093 | no | no |
| `inspect_evals/lab_bench_seqqa` | `inspect_evals/precision_choice` | choice | 600 | 22.7% | 17.4% | format_only | 22.7% | +0.000 | format_only | **yes** |
| `inspect_evals/lab_bench_suppqa` | `inspect_evals/precision_choice` | choice | 82 | 31.7% | 16.8% | format_only | 17.1% | -0.146 | no | no |
| `inspect_evals/lab_bench_tableqa` | `inspect_evals/precision_choice` | choice | 244 | 20.1% | 13.0% | format_only | 20.1% | +0.000 | format_only | **yes** |
| `inspect_evals/macbench` | `inspect_evals/macbench_scorer` | choice | 1153 | 0.0% | n/a | empty | 0.0% | +0.000 | no | no |
| `inspect_evals/mmlu_0_shot` | `inspect_ai/choice` | choice | 13937 | 26.8% | 25.0% | format_only | 23.0% | -0.038 | no | no |
| `inspect_evals/mmlu_5_shot` | `inspect_ai/choice` | choice | 14015 | 26.9% | 24.8% | echo | 24.1% | -0.028 | no | no |
| `inspect_evals/mmlu_pro` | `inspect_ai/choice` | choice | 12032 | 11.7% | 10.0% | format_only | 11.7% | +0.000 | format_only | **yes** |
| `inspect_evals/musr` | `inspect_ai/choice` | choice | 250 | 50.0% | 50.8% | format_only | 50.0% | +0.000 | format_only | **yes** |
| `inspect_evals/onet_m6` | `inspect_ai/choice` | choice | 397 | 21.2% | 19.5% | format_only | 19.9% | -0.013 | no | no |
| `inspect_evals/paws` | `inspect_ai/pattern` | bare | 8000 | 55.8% | 49.6% | empty | 0.0% | -0.558 | no | no |
| `inspect_evals/pre_flight` | `inspect_ai/choice` | choice | 300 | 44.0% | 24.9% | format_only | 24.3% | -0.197 | no | no |
| `inspect_evals/pubmedqa` | `inspect_ai/choice` | choice | 500 | 55.2% | 34.8% | format_only | 55.2% | +0.000 | format_only | **yes** |
| `inspect_evals/race_h` | `inspect_ai/choice` | choice | 3498 | 27.2% | 25.0% | format_only | 21.6% | -0.056 | no | no |
| `inspect_evals/sec_qa_v1` | `inspect_ai/choice` | choice | 110 | 29.1% | 24.7% | format_only | 19.1% | -0.100 | no | no |
| `inspect_evals/sec_qa_v1_5_shot` | `inspect_ai/choice` | choice | 110 | 29.1% | 24.7% | format_only | 19.1% | -0.100 | no | no |
| `inspect_evals/sec_qa_v2` | `inspect_ai/choice` | choice | 100 | 31.0% | 22.6% | format_only | 21.0% | -0.100 | no | no |
| `inspect_evals/sec_qa_v2_5_shot` | `inspect_ai/choice` | choice | 100 | 31.0% | 22.6% | format_only | 21.0% | -0.100 | no | no |
| `inspect_evals/squad` | `inspect_ai/exact` | bare | 11873 | 50.1% | n/a | empty | 0.0% | -0.500 | no | no |
| `inspect_evals/squad` | `inspect_ai/f1` | bare | 11873 | 50.1% | n/a | echo | 4.1% | -0.459 | no | no |
| `inspect_evals/truthfulqa` | `inspect_ai/choice` | choice | 817 | 24.8% | 10.5% | format_only | 24.8% | +0.000 | format_only | **yes** |
| `inspect_evals/vstar_bench_attribute_recognition` | `inspect_ai/choice` | choice | 115 | 29.6% | 24.0% | format_only | 29.6% | +0.000 | format_only | **yes** |
| `inspect_evals/vstar_bench_spatial_relationship_reasoning` | `inspect_ai/choice` | choice | 76 | 51.3% | 47.4% | format_only | 48.7% | -0.026 | no | no |
| `inspect_evals/winogrande` | `inspect_ai/choice` | choice | 1267 | 50.4% | 50.0% | format_only | 49.6% | -0.009 | no | no |
| `inspect_evals/wmdp_bio` | `inspect_ai/choice` | choice | 1273 | 26.6% | 24.7% | format_only | 24.7% | -0.019 | no | no |
| `inspect_evals/wmdp_chem` | `inspect_ai/choice` | choice | 408 | 26.5% | 26.2% | format_only | 23.5% | -0.029 | no | no |
| `inspect_evals/wmdp_cyber` | `inspect_ai/choice` | choice | 1987 | 26.6% | 25.0% | format_only | 26.6% | +0.000 | format_only | **yes** |

`collision` marks a flag that rests **only** on `format_only` and `majority` being the same completion. `format_only` is defined as the task's answer template carrying the placeholder `A`; `majority` is the modal target written in that same template. Where the modal target *is* `A` they are one string, they score identically, and the `>=` in the flag rule fires on a tie between a member and itself. The rule is unchanged (section 8.5: a tie flags, and weakening a rule after seeing data is worse) -- the flag is marked instead.

* `inspect_evals/lab_bench_dbqa`: the only flagging member is `format_only`, and the completion it was scored on ('ANSWER: A') is the completion `majority` was scored on. The task's modal target is 'A', which is the placeholder `format_only` carries, so the two members are the same string and the tie is definitional rather than a finding.
* `inspect_evals/lab_bench_litqa`: the only flagging member is `format_only`, and the completion it was scored on ('ANSWER: A') is the completion `majority` was scored on. The task's modal target is 'A', which is the placeholder `format_only` carries, so the two members are the same string and the tie is definitional rather than a finding.
* `inspect_evals/lab_bench_seqqa`: the only flagging member is `format_only`, and the completion it was scored on ('ANSWER: A') is the completion `majority` was scored on. The task's modal target is 'A', which is the placeholder `format_only` carries, so the two members are the same string and the tie is definitional rather than a finding.
* `inspect_evals/lab_bench_tableqa`: the only flagging member is `format_only`, and the completion it was scored on ('ANSWER: A') is the completion `majority` was scored on. The task's modal target is 'A', which is the placeholder `format_only` carries, so the two members are the same string and the tie is definitional rather than a finding.
* `inspect_evals/mmlu_pro`: the only flagging member is `format_only`, and the completion it was scored on ('ANSWER: A') is the completion `majority` was scored on. The task's modal target is 'A', which is the placeholder `format_only` carries, so the two members are the same string and the tie is definitional rather than a finding.
* `inspect_evals/musr`: the only flagging member is `format_only`, and the completion it was scored on ('ANSWER: A') is the completion `majority` was scored on. The task's modal target is 'A', which is the placeholder `format_only` carries, so the two members are the same string and the tie is definitional rather than a finding.
* `inspect_evals/pubmedqa`: the only flagging member is `format_only`, and the completion it was scored on ('ANSWER: A') is the completion `majority` was scored on. The task's modal target is 'A', which is the placeholder `format_only` carries, so the two members are the same string and the tie is definitional rather than a finding.
* `inspect_evals/truthfulqa`: the only flagging member is `format_only`, and the completion it was scored on ('ANSWER: A') is the completion `majority` was scored on. The task's modal target is 'A', which is the placeholder `format_only` carries, so the two members are the same string and the tie is definitional rather than a finding.
* `inspect_evals/vstar_bench_attribute_recognition`: the only flagging member is `format_only`, and the completion it was scored on ('ANSWER: A') is the completion `majority` was scored on. The task's modal target is 'A', which is the placeholder `format_only` carries, so the two members are the same string and the tie is definitional rather than a finding.
* `inspect_evals/wmdp_cyber`: the only flagging member is `format_only`, and the completion it was scored on ('ANSWER: A') is the completion `majority` was scored on. The task's modal target is 'A', which is the placeholder `format_only` carries, so the two members are the same string and the tie is definitional rather than a finding.

## What the rendering rule changed

Every member is defined semantically and then written down in the task's own answer template when it declares one. Both forms are scored. On a task that declares no template the two arms are identical by construction, and the rows below show that rather than asserting it.

| task | template | majority raw | majority rendered | best CF raw | best CF rendered | flagged raw | flagged rendered |
|---|---|---|---|---|---|---|---|
| `inspect_evals/aime2024` | bare | 6.7% | 6.7% | all_labels 3.3% | all_labels 3.3% | no | no |
| `inspect_evals/aime2025` | bare | 3.3% | 3.3% | empty 0.0% | empty 0.0% | no | no |
| `inspect_evals/aime2026` | bare | 3.3% | 3.3% | empty 0.0% | empty 0.0% | no | no |
| `inspect_evals/arc_challenge` | choice | 0.0% | 26.5% | format_only 22.7% | format_only 22.7% | yes | no |
| `inspect_evals/arc_easy` | choice | 0.0% | 26.6% | format_only 25.1% | format_only 25.1% | yes | no |
| `inspect_evals/bbeh` | bare | 3.9% | 3.9% | empty 0.0% | empty 0.0% | no | no |
| `inspect_evals/bbeh_mini` | bare | 4.6% | 4.6% | empty 0.2% | empty 0.2% | no | no |
| `inspect_evals/bbh` | bare | 0.0% | 15.8% | echo 26.2% | echo 26.2% | yes | yes |
| `inspect_evals/bbq` | choice | 0.0% | 33.4% | format_only 33.3% | format_only 33.3% | yes | no |
| `inspect_evals/boolq` | bare | 62.2% | 62.2% | empty 0.0% | empty 0.0% | no | no |
| `inspect_evals/chembench` | choice | 0.0% | 0.0% | empty 0.0% | empty 0.0% | no | no |
| `inspect_evals/commonsense_qa` | choice | 0.0% | 20.9% | format_only 19.6% | format_only 19.6% | yes | no |
| `inspect_evals/drop` | bare | 7.3% | 7.3% | echo 2.3% | echo 2.3% | no | no |
| `inspect_evals/gsm8k` | bare | 3.0% | 3.0% | echo 2.1% | echo 2.1% | no | no |
| `inspect_evals/hellaswag` | choice | 0.0% | 25.7% | format_only 25.0% | format_only 25.0% | yes | no |
| `inspect_evals/lab_bench_cloning_scenarios` | choice | 0.0% | 27.3% | format_only 15.2% | format_only 15.2% | yes | no |
| `inspect_evals/lab_bench_dbqa` | choice | 0.0% | 23.1% | format_only 23.1% | format_only 23.1% | yes | yes |
| `inspect_evals/lab_bench_figqa` | choice | 0.0% | 19.3% | format_only 18.2% | format_only 18.2% | yes | no |
| `inspect_evals/lab_bench_litqa` | choice | 0.0% | 22.6% | format_only 22.6% | format_only 22.6% | yes | yes |
| `inspect_evals/lab_bench_protocolqa` | choice | 0.0% | 26.9% | format_only 17.6% | format_only 17.6% | yes | no |
| `inspect_evals/lab_bench_seqqa` | choice | 0.0% | 22.7% | format_only 22.7% | format_only 22.7% | yes | yes |
| `inspect_evals/lab_bench_suppqa` | choice | 0.0% | 31.7% | format_only 17.1% | format_only 17.1% | yes | no |
| `inspect_evals/lab_bench_tableqa` | choice | 0.0% | 20.1% | format_only 20.1% | format_only 20.1% | yes | yes |
| `inspect_evals/macbench` | choice | 0.0% | 0.0% | empty 0.0% | empty 0.0% | no | no |
| `inspect_evals/mmlu_0_shot` | choice | 0.0% | 26.8% | format_only 23.0% | format_only 23.0% | yes | no |
| `inspect_evals/mmlu_5_shot` | choice | 0.0% | 26.9% | echo 24.1% | echo 24.1% | yes | no |
| `inspect_evals/mmlu_pro` | choice | 0.0% | 11.7% | format_only 11.7% | format_only 11.7% | yes | yes |
| `inspect_evals/musr` | choice | 0.0% | 50.0% | format_only 50.0% | format_only 50.0% | yes | yes |
| `inspect_evals/onet_m6` | choice | 0.0% | 21.2% | format_only 19.9% | format_only 19.9% | yes | no |
| `inspect_evals/paws` | bare | 55.8% | 55.8% | empty 0.0% | empty 0.0% | no | no |
| `inspect_evals/pre_flight` | choice | 0.0% | 44.0% | format_only 24.3% | format_only 24.3% | yes | no |
| `inspect_evals/pubmedqa` | choice | 0.0% | 55.2% | format_only 55.2% | format_only 55.2% | yes | yes |
| `inspect_evals/race_h` | choice | 0.0% | 27.2% | format_only 21.6% | format_only 21.6% | yes | no |
| `inspect_evals/sec_qa_v1` | choice | 0.0% | 29.1% | format_only 19.1% | format_only 19.1% | yes | no |
| `inspect_evals/sec_qa_v1_5_shot` | choice | 0.0% | 29.1% | format_only 19.1% | format_only 19.1% | yes | no |
| `inspect_evals/sec_qa_v2` | choice | 0.0% | 31.0% | format_only 21.0% | format_only 21.0% | yes | no |
| `inspect_evals/sec_qa_v2_5_shot` | choice | 0.0% | 31.0% | format_only 21.0% | format_only 21.0% | yes | no |
| `inspect_evals/squad` | bare | 50.1% | 50.1% | empty 0.0% | empty 0.0% | no | no |
| `inspect_evals/squad` | bare | 50.1% | 50.1% | echo 4.1% | echo 4.1% | no | no |
| `inspect_evals/truthfulqa` | choice | 0.0% | 24.8% | format_only 24.8% | format_only 24.8% | yes | yes |
| `inspect_evals/vstar_bench_attribute_recognition` | choice | 0.0% | 29.6% | format_only 29.6% | format_only 29.6% | yes | yes |
| `inspect_evals/vstar_bench_spatial_relationship_reasoning` | choice | 0.0% | 51.3% | format_only 48.7% | format_only 48.7% | yes | no |
| `inspect_evals/winogrande` | choice | 0.0% | 50.4% | format_only 49.6% | format_only 49.6% | yes | no |
| `inspect_evals/wmdp_bio` | choice | 0.0% | 26.6% | format_only 24.7% | format_only 24.7% | yes | no |
| `inspect_evals/wmdp_chem` | choice | 0.0% | 26.5% | format_only 23.5% | format_only 23.5% | yes | no |
| `inspect_evals/wmdp_cyber` | choice | 0.0% | 26.6% | format_only 26.6% | format_only 26.6% | yes | yes |

34 of 46 tasks here declare an answer template. The two arms disagree on 22.

**What this table is showing.** On 32 of the 34 task(s) here that declare an answer template, the raw arm's `majority` baseline is **0.0%** while the rendered arm's is not. That is instrument defect 003 preserved as a number: a bare label such as `C` is not an answer a multiple-choice scorer can read, so the chance line collapses to zero and then anything that scores at all clears it. That is why 22 task(s) are flagged on the raw arm and not on the rendered one. The raw arm is not the stricter reading of the two; it is the broken one, kept visible on purpose. In the other direction, rendered `all_labels` scores **0.000** on 32 of 34 templated task(s): written properly as `ANSWER: A, B, C, D`, the multiple-choice parser rejects a multi-option answer to a single-answer question. So `choice()` is genuinely tight against naming every label, and because most reachable tasks are scored by `choice()`, that is a large part of why the headline number is small rather than large.

Both defects are written up in `INSTRUMENT_LESSONS.md`.

## Every battery member, every task -- raw arm

| task | scorer | empty | whitespace | refusal | all_labels | all_letters | echo | boilerplate | format_only | majority | uniform |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `inspect_evals/aime2024` | `inspect_evals/aime_scorer` | 0.0% | 0.0% | 0.0% | 3.3% | 0.0% | 0.0% | 0.0% | 0.0% | 6.7% | 3.3% |
| `inspect_evals/aime2025` | `inspect_evals/aime_scorer` | 0.0% | 0.0% | 0.0% | n/a | 0.0% | 0.0% | 0.0% | 0.0% | 3.3% | n/a |
| `inspect_evals/aime2026` | `inspect_evals/aime_scorer` | 0.0% | 0.0% | 0.0% | n/a | 0.0% | 0.0% | 0.0% | 0.0% | 3.3% | n/a |
| `inspect_evals/arc_challenge` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 22.7% | 0.0% | 0.0% |
| `inspect_evals/arc_easy` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 25.1% | 0.0% | 0.0% |
| `inspect_evals/bbeh` | `inspect_evals/bbeh_scorer` | 0.0% | 0.0% | 0.0% | n/a | 0.0% | 0.0% | 0.0% | 0.0% | 3.9% | n/a |
| `inspect_evals/bbeh_mini` | `inspect_evals/bbeh_scorer` | 0.2% | 0.2% | 0.0% | n/a | 0.0% | 0.0% | 0.0% | 0.0% | 4.6% | n/a |
| `inspect_evals/bbh` | `inspect_evals/bbh_scorer` | 0.0% | 0.0% | 0.0% | n/a | 0.0% | 26.2% | 0.0% | 14.9% | 0.0% | n/a |
| `inspect_evals/bbq` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 33.3% | 0.0% | 0.0% |
| `inspect_evals/boolq` | `inspect_ai/pattern` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 62.2% | 50.0% |
| `inspect_evals/chembench` | `inspect_evals/chembench_scorer` | 0.0% | 0.0% | 0.0% | n/a | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | n/a |
| `inspect_evals/commonsense_qa` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 19.6% | 0.0% | 0.0% |
| `inspect_evals/drop` | `inspect_ai/f1` | 0.0% | 0.0% | 0.1% | n/a | 0.0% | 2.3% | 0.2% | 0.0% | 7.3% | n/a |
| `inspect_evals/gsm8k` | `inspect_ai/match` | 0.0% | 0.0% | 0.0% | n/a | 0.0% | 2.1% | 0.0% | 0.0% | 3.0% | n/a |
| `inspect_evals/hellaswag` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 25.0% | 0.0% | 0.0% |
| `inspect_evals/lab_bench_cloning_scenarios` | `inspect_evals/precision_choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 15.2% | 0.0% | 0.0% |
| `inspect_evals/lab_bench_dbqa` | `inspect_evals/precision_choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 23.1% | 0.0% | 0.0% |
| `inspect_evals/lab_bench_figqa` | `inspect_evals/precision_choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 18.2% | 0.0% | 0.0% |
| `inspect_evals/lab_bench_litqa` | `inspect_evals/precision_choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 22.6% | 0.0% | 0.0% |
| `inspect_evals/lab_bench_protocolqa` | `inspect_evals/precision_choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 17.6% | 0.0% | 0.0% |
| `inspect_evals/lab_bench_seqqa` | `inspect_evals/precision_choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 22.7% | 0.0% | 0.0% |
| `inspect_evals/lab_bench_suppqa` | `inspect_evals/precision_choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 17.1% | 0.0% | 0.0% |
| `inspect_evals/lab_bench_tableqa` | `inspect_evals/precision_choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 20.1% | 0.0% | 0.0% |
| `inspect_evals/macbench` | `inspect_evals/macbench_scorer` | 0.0% | 0.0% | 0.0% | n/a | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | n/a |
| `inspect_evals/mmlu_0_shot` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 23.0% | 0.0% | 0.0% |
| `inspect_evals/mmlu_5_shot` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 24.1% | 0.0% | 23.0% | 0.0% | 0.0% |
| `inspect_evals/mmlu_pro` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 11.7% | 0.0% | 0.0% |
| `inspect_evals/musr` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 50.0% | 0.0% | 0.0% |
| `inspect_evals/onet_m6` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 19.9% | 0.0% | 0.0% |
| `inspect_evals/paws` | `inspect_ai/pattern` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 55.8% | 49.6% |
| `inspect_evals/pre_flight` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 24.3% | 0.0% | 0.0% |
| `inspect_evals/pubmedqa` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 55.2% | 0.0% | 0.0% |
| `inspect_evals/race_h` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 21.6% | 0.0% | 0.0% |
| `inspect_evals/sec_qa_v1` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 19.1% | 0.0% | 0.0% |
| `inspect_evals/sec_qa_v1_5_shot` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 19.1% | 0.0% | 0.0% |
| `inspect_evals/sec_qa_v2` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 21.0% | 0.0% | 0.0% |
| `inspect_evals/sec_qa_v2_5_shot` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 21.0% | 0.0% | 0.0% |
| `inspect_evals/squad` | `inspect_ai/exact` | 0.0% | 0.0% | 0.0% | n/a | 0.0% | 0.0% | 0.0% | 0.0% | 50.1% | n/a |
| `inspect_evals/squad` | `inspect_ai/f1` | 0.0% | 0.0% | 0.2% | n/a | 0.0% | 4.1% | 0.6% | 0.0% | 50.1% | n/a |
| `inspect_evals/truthfulqa` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 24.8% | 0.0% | 0.0% |
| `inspect_evals/vstar_bench_attribute_recognition` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 29.6% | 0.0% | 0.0% |
| `inspect_evals/vstar_bench_spatial_relationship_reasoning` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 48.7% | 0.0% | 0.0% |
| `inspect_evals/winogrande` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 49.6% | 0.0% | 0.0% |
| `inspect_evals/wmdp_bio` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 24.7% | 0.0% | 0.0% |
| `inspect_evals/wmdp_chem` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 23.5% | 0.0% | 0.0% |
| `inspect_evals/wmdp_cyber` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 26.6% | 0.0% | 0.0% |

## Every battery member, every task -- rendered arm

| task | scorer | empty | whitespace | refusal | all_labels | all_letters | echo | boilerplate | format_only | majority | uniform |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `inspect_evals/aime2024` | `inspect_evals/aime_scorer` | 0.0% | 0.0% | 0.0% | 3.3% | 0.0% | 0.0% | 0.0% | 0.0% | 6.7% | 3.3% |
| `inspect_evals/aime2025` | `inspect_evals/aime_scorer` | 0.0% | 0.0% | 0.0% | n/a | 0.0% | 0.0% | 0.0% | 0.0% | 3.3% | n/a |
| `inspect_evals/aime2026` | `inspect_evals/aime_scorer` | 0.0% | 0.0% | 0.0% | n/a | 0.0% | 0.0% | 0.0% | 0.0% | 3.3% | n/a |
| `inspect_evals/arc_challenge` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 22.7% | 26.5% | 25.2% |
| `inspect_evals/arc_easy` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 25.1% | 26.6% | 19.8% |
| `inspect_evals/bbeh` | `inspect_evals/bbeh_scorer` | 0.0% | 0.0% | 0.0% | n/a | 0.0% | 0.0% | 0.0% | 0.0% | 3.9% | n/a |
| `inspect_evals/bbeh_mini` | `inspect_evals/bbeh_scorer` | 0.2% | 0.2% | 0.0% | n/a | 0.0% | 0.0% | 0.0% | 0.0% | 4.6% | n/a |
| `inspect_evals/bbh` | `inspect_evals/bbh_scorer` | 0.0% | 0.0% | 0.0% | n/a | 0.0% | 26.2% | 0.0% | 14.9% | 15.8% | n/a |
| `inspect_evals/bbq` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 33.3% | 33.4% | 33.3% |
| `inspect_evals/boolq` | `inspect_ai/pattern` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 62.2% | 50.0% |
| `inspect_evals/chembench` | `inspect_evals/chembench_scorer` | 0.0% | 0.0% | 0.0% | n/a | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | n/a |
| `inspect_evals/commonsense_qa` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 19.6% | 20.9% | 20.1% |
| `inspect_evals/drop` | `inspect_ai/f1` | 0.0% | 0.0% | 0.1% | n/a | 0.0% | 2.3% | 0.2% | 0.0% | 7.3% | n/a |
| `inspect_evals/gsm8k` | `inspect_ai/match` | 0.0% | 0.0% | 0.0% | n/a | 0.0% | 2.1% | 0.0% | 0.0% | 3.0% | n/a |
| `inspect_evals/hellaswag` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 25.0% | 25.7% | 24.7% |
| `inspect_evals/lab_bench_cloning_scenarios` | `inspect_evals/precision_choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 15.2% | 27.3% | 23.6% |
| `inspect_evals/lab_bench_dbqa` | `inspect_evals/precision_choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 23.1% | 23.1% | 19.0% |
| `inspect_evals/lab_bench_figqa` | `inspect_evals/precision_choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 18.2% | 19.3% | 13.8% |
| `inspect_evals/lab_bench_litqa` | `inspect_evals/precision_choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 22.6% | 22.6% | 11.0% |
| `inspect_evals/lab_bench_protocolqa` | `inspect_evals/precision_choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 17.6% | 26.9% | 15.9% |
| `inspect_evals/lab_bench_seqqa` | `inspect_evals/precision_choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 22.7% | 22.7% | 17.4% |
| `inspect_evals/lab_bench_suppqa` | `inspect_evals/precision_choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 17.1% | 31.7% | 16.8% |
| `inspect_evals/lab_bench_tableqa` | `inspect_evals/precision_choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 20.1% | 20.1% | 13.0% |
| `inspect_evals/macbench` | `inspect_evals/macbench_scorer` | 0.0% | 0.0% | 0.0% | n/a | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | n/a |
| `inspect_evals/mmlu_0_shot` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 23.0% | 26.8% | 25.0% |
| `inspect_evals/mmlu_5_shot` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 24.1% | 0.0% | 23.0% | 26.9% | 24.8% |
| `inspect_evals/mmlu_pro` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 11.7% | 11.7% | 10.0% |
| `inspect_evals/musr` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 50.0% | 50.0% | 50.8% |
| `inspect_evals/onet_m6` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 19.9% | 21.2% | 19.5% |
| `inspect_evals/paws` | `inspect_ai/pattern` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 55.8% | 49.6% |
| `inspect_evals/pre_flight` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 24.3% | 44.0% | 24.9% |
| `inspect_evals/pubmedqa` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 55.2% | 55.2% | 34.8% |
| `inspect_evals/race_h` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 21.6% | 27.2% | 25.0% |
| `inspect_evals/sec_qa_v1` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 19.1% | 29.1% | 24.7% |
| `inspect_evals/sec_qa_v1_5_shot` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 19.1% | 29.1% | 24.7% |
| `inspect_evals/sec_qa_v2` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 21.0% | 31.0% | 22.6% |
| `inspect_evals/sec_qa_v2_5_shot` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 21.0% | 31.0% | 22.6% |
| `inspect_evals/squad` | `inspect_ai/exact` | 0.0% | 0.0% | 0.0% | n/a | 0.0% | 0.0% | 0.0% | 0.0% | 50.1% | n/a |
| `inspect_evals/squad` | `inspect_ai/f1` | 0.0% | 0.0% | 0.2% | n/a | 0.0% | 4.1% | 0.6% | 0.0% | 50.1% | n/a |
| `inspect_evals/truthfulqa` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 24.8% | 24.8% | 10.5% |
| `inspect_evals/vstar_bench_attribute_recognition` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 29.6% | 29.6% | 24.0% |
| `inspect_evals/vstar_bench_spatial_relationship_reasoning` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 48.7% | 51.3% | 47.4% |
| `inspect_evals/winogrande` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 49.6% | 50.4% | 50.0% |
| `inspect_evals/wmdp_bio` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 24.7% | 26.6% | 24.7% |
| `inspect_evals/wmdp_chem` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 23.5% | 26.5% | 26.2% |
| `inspect_evals/wmdp_cyber` | `inspect_ai/choice` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 26.6% | 26.6% | 25.0% |

## Counts, not rates (rendered arm)

| task | scorer | member | correct | scored | completion scored |
|---|---|---|---|---|---|
| `inspect_evals/aime2024` | `inspect_evals/aime_scorer` | empty | 0 | 30 | `` |
| `inspect_evals/aime2024` | `inspect_evals/aime_scorer` | whitespace | 0 | 30 | ` ` |
| `inspect_evals/aime2024` | `inspect_evals/aime_scorer` | refusal | 0 | 30 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/aime2024` | `inspect_evals/aime_scorer` | all_labels | 1 | 30 | `104 110 113 116 127 197 204 211 23 236 25 294 315 321 33 371` |
| `inspect_evals/aime2024` | `inspect_evals/aime_scorer` | all_letters | 0 | 30 | `A B C D E` |
| `inspect_evals/aime2024` | `inspect_evals/aime_scorer` | echo | 0 | 30 | `Every morning Aya goes for a $9$-kilometer-long walk and sto` |
| `inspect_evals/aime2024` | `inspect_evals/aime_scorer` | boilerplate | 0 | 30 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/aime2024` | `inspect_evals/aime_scorer` | format_only | 0 | 30 | `ANSWER: A` |
| `inspect_evals/aime2024` | `inspect_evals/aime_scorer` | majority | 2 | 30 | `104` |
| `inspect_evals/aime2024` | `inspect_evals/aime_scorer` | uniform | 5 | 150 | `385` |
| `inspect_evals/aime2025` | `inspect_evals/aime_scorer` | empty | 0 | 30 | `` |
| `inspect_evals/aime2025` | `inspect_evals/aime_scorer` | whitespace | 0 | 30 | ` ` |
| `inspect_evals/aime2025` | `inspect_evals/aime_scorer` | refusal | 0 | 30 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/aime2025` | `inspect_evals/aime_scorer` | all_letters | 0 | 30 | `A B C D E` |
| `inspect_evals/aime2025` | `inspect_evals/aime_scorer` | echo | 0 | 30 | `Find the sum of all integer bases $b>9$ for which $17_b$ is ` |
| `inspect_evals/aime2025` | `inspect_evals/aime_scorer` | boilerplate | 0 | 30 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/aime2025` | `inspect_evals/aime_scorer` | format_only | 0 | 30 | `ANSWER: A` |
| `inspect_evals/aime2025` | `inspect_evals/aime_scorer` | majority | 1 | 30 | `104` |
| `inspect_evals/aime2026` | `inspect_evals/aime_scorer` | empty | 0 | 30 | `` |
| `inspect_evals/aime2026` | `inspect_evals/aime_scorer` | whitespace | 0 | 30 | ` ` |
| `inspect_evals/aime2026` | `inspect_evals/aime_scorer` | refusal | 0 | 30 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/aime2026` | `inspect_evals/aime_scorer` | all_letters | 0 | 30 | `A B C D E` |
| `inspect_evals/aime2026` | `inspect_evals/aime_scorer` | echo | 0 | 30 | `Patrick started walking at a constant rate along a straight ` |
| `inspect_evals/aime2026` | `inspect_evals/aime_scorer` | boilerplate | 0 | 30 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/aime2026` | `inspect_evals/aime_scorer` | format_only | 0 | 30 | `ANSWER: A` |
| `inspect_evals/aime2026` | `inspect_evals/aime_scorer` | majority | 1 | 30 | `107` |
| `inspect_evals/arc_challenge` | `inspect_ai/choice` | empty | 0 | 1172 | `` |
| `inspect_evals/arc_challenge` | `inspect_ai/choice` | whitespace | 0 | 1172 | ` ` |
| `inspect_evals/arc_challenge` | `inspect_ai/choice` | refusal | 0 | 1172 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/arc_challenge` | `inspect_ai/choice` | all_labels | 0 | 1172 | `ANSWER: B, C, D, A` |
| `inspect_evals/arc_challenge` | `inspect_ai/choice` | all_letters | 0 | 1172 | `A B C D E` |
| `inspect_evals/arc_challenge` | `inspect_ai/choice` | echo | 0 | 1172 | `A student is investigating the temperature at which evaporat` |
| `inspect_evals/arc_challenge` | `inspect_ai/choice` | boilerplate | 0 | 1172 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/arc_challenge` | `inspect_ai/choice` | format_only | 266 | 1172 | `ANSWER: A` |
| `inspect_evals/arc_challenge` | `inspect_ai/choice` | majority | 311 | 1172 | `ANSWER: B` |
| `inspect_evals/arc_challenge` | `inspect_ai/choice` | uniform | 1476 | 5860 | `ANSWER: A` |
| `inspect_evals/arc_easy` | `inspect_ai/choice` | empty | 0 | 2376 | `` |
| `inspect_evals/arc_easy` | `inspect_ai/choice` | whitespace | 0 | 2376 | ` ` |
| `inspect_evals/arc_easy` | `inspect_ai/choice` | refusal | 0 | 2376 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/arc_easy` | `inspect_ai/choice` | all_labels | 0 | 2376 | `ANSWER: C, A, B, D, E` |
| `inspect_evals/arc_easy` | `inspect_ai/choice` | all_letters | 0 | 2376 | `A B C D E` |
| `inspect_evals/arc_easy` | `inspect_ai/choice` | echo | 0 | 2376 | `When a bottle of strong perfume is opened at the front of a ` |
| `inspect_evals/arc_easy` | `inspect_ai/choice` | boilerplate | 0 | 2376 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/arc_easy` | `inspect_ai/choice` | format_only | 596 | 2376 | `ANSWER: A` |
| `inspect_evals/arc_easy` | `inspect_ai/choice` | majority | 633 | 2376 | `ANSWER: C` |
| `inspect_evals/arc_easy` | `inspect_ai/choice` | uniform | 2350 | 11880 | `ANSWER: D` |
| `inspect_evals/bbeh` | `inspect_evals/bbeh_scorer` | empty | 2 | 4519 | `` |
| `inspect_evals/bbeh` | `inspect_evals/bbeh_scorer` | whitespace | 2 | 4519 | ` ` |
| `inspect_evals/bbeh` | `inspect_evals/bbeh_scorer` | refusal | 0 | 4519 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/bbeh` | `inspect_evals/bbeh_scorer` | all_letters | 0 | 4519 | `A B C D E` |
| `inspect_evals/bbeh` | `inspect_evals/bbeh_scorer` | echo | 0 | 4519 | `Here are three (post, reply) pairs from Reddit. Your task is` |
| `inspect_evals/bbeh` | `inspect_evals/bbeh_scorer` | boilerplate | 0 | 4519 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/bbeh` | `inspect_evals/bbeh_scorer` | format_only | 0 | 4519 | `ANSWER: A` |
| `inspect_evals/bbeh` | `inspect_evals/bbeh_scorer` | majority | 175 | 4519 | `(A)` |
| `inspect_evals/bbeh_mini` | `inspect_evals/bbeh_scorer` | empty | 1 | 460 | `` |
| `inspect_evals/bbeh_mini` | `inspect_evals/bbeh_scorer` | whitespace | 1 | 460 | ` ` |
| `inspect_evals/bbeh_mini` | `inspect_evals/bbeh_scorer` | refusal | 0 | 460 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/bbeh_mini` | `inspect_evals/bbeh_scorer` | all_letters | 0 | 460 | `A B C D E` |
| `inspect_evals/bbeh_mini` | `inspect_evals/bbeh_scorer` | echo | 0 | 460 | `Here are three (post, reply) pairs from Reddit. Your task is` |
| `inspect_evals/bbeh_mini` | `inspect_evals/bbeh_scorer` | boilerplate | 0 | 460 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/bbeh_mini` | `inspect_evals/bbeh_scorer` | format_only | 0 | 460 | `ANSWER: A` |
| `inspect_evals/bbeh_mini` | `inspect_evals/bbeh_scorer` | majority | 21 | 460 | `(D)` |
| `inspect_evals/bbh` | `inspect_evals/bbh_scorer` | empty | 0 | 6508 | `` |
| `inspect_evals/bbh` | `inspect_evals/bbh_scorer` | whitespace | 0 | 6508 | ` ` |
| `inspect_evals/bbh` | `inspect_evals/bbh_scorer` | refusal | 0 | 6508 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/bbh` | `inspect_evals/bbh_scorer` | all_letters | 0 | 6508 | `A B C D E` |
| `inspect_evals/bbh` | `inspect_evals/bbh_scorer` | echo | 1702 | 6508 | `Make sure you output your answer on the last line as 'ANSWER` |
| `inspect_evals/bbh` | `inspect_evals/bbh_scorer` | boilerplate | 0 | 6508 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/bbh` | `inspect_evals/bbh_scorer` | format_only | 969 | 6508 | `ANSWER: A` |
| `inspect_evals/bbh` | `inspect_evals/bbh_scorer` | majority | 1030 | 6508 | `B` |
| `inspect_evals/bbq` | `inspect_ai/choice` | empty | 0 | 58492 | `` |
| `inspect_evals/bbq` | `inspect_ai/choice` | whitespace | 0 | 58492 | ` ` |
| `inspect_evals/bbq` | `inspect_ai/choice` | refusal | 0 | 58492 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/bbq` | `inspect_ai/choice` | all_labels | 0 | 58492 | `ANSWER: C, B, A` |
| `inspect_evals/bbq` | `inspect_ai/choice` | all_letters | 0 | 58492 | `A B C D E` |
| `inspect_evals/bbq` | `inspect_ai/choice` | echo | 0 | 58492 | `Context: I saw a grandson and their grandfather last week ou` |
| `inspect_evals/bbq` | `inspect_ai/choice` | boilerplate | 0 | 58492 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/bbq` | `inspect_ai/choice` | format_only | 19469 | 58492 | `ANSWER: A` |
| `inspect_evals/bbq` | `inspect_ai/choice` | majority | 19514 | 58492 | `ANSWER: C` |
| `inspect_evals/bbq` | `inspect_ai/choice` | uniform | 97458 | 292460 | `ANSWER: A` |
| `inspect_evals/boolq` | `inspect_ai/pattern` | empty | 0 | 3270 | `` |
| `inspect_evals/boolq` | `inspect_ai/pattern` | whitespace | 0 | 3270 | ` ` |
| `inspect_evals/boolq` | `inspect_ai/pattern` | refusal | 0 | 3270 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/boolq` | `inspect_ai/pattern` | all_labels | 0 | 3270 | `Yes No` |
| `inspect_evals/boolq` | `inspect_ai/pattern` | all_letters | 0 | 3270 | `A B C D E` |
| `inspect_evals/boolq` | `inspect_ai/pattern` | echo | 0 | 3270 | ` Given a passage, answer the subsequent question with either` |
| `inspect_evals/boolq` | `inspect_ai/pattern` | boilerplate | 0 | 3270 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/boolq` | `inspect_ai/pattern` | format_only | 0 | 3270 | `ANSWER: A` |
| `inspect_evals/boolq` | `inspect_ai/pattern` | majority | 2033 | 3270 | `Yes` |
| `inspect_evals/boolq` | `inspect_ai/pattern` | uniform | 8173 | 16350 | `Yes` |
| `inspect_evals/chembench` | `inspect_evals/chembench_scorer` | empty | 0 | 2785 | `` |
| `inspect_evals/chembench` | `inspect_evals/chembench_scorer` | whitespace | 0 | 2785 | ` ` |
| `inspect_evals/chembench` | `inspect_evals/chembench_scorer` | refusal | 0 | 2785 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/chembench` | `inspect_evals/chembench_scorer` | all_letters | 0 | 2785 | `A B C D E` |
| `inspect_evals/chembench` | `inspect_evals/chembench_scorer` | echo | 0 | 2785 | `Which aryl halides are most useful in cross-coupling reactio` |
| `inspect_evals/chembench` | `inspect_evals/chembench_scorer` | boilerplate | 0 | 2785 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/chembench` | `inspect_evals/chembench_scorer` | format_only | 0 | 2785 | `ANSWER: A` |
| `inspect_evals/chembench` | `inspect_evals/chembench_scorer` | majority | 0 | 2785 | `ANSWER: A` |
| `inspect_evals/commonsense_qa` | `inspect_ai/choice` | empty | 0 | 1221 | `` |
| `inspect_evals/commonsense_qa` | `inspect_ai/choice` | whitespace | 0 | 1221 | ` ` |
| `inspect_evals/commonsense_qa` | `inspect_ai/choice` | refusal | 0 | 1221 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/commonsense_qa` | `inspect_ai/choice` | all_labels | 0 | 1221 | `ANSWER: B, D, C, A, E` |
| `inspect_evals/commonsense_qa` | `inspect_ai/choice` | all_letters | 0 | 1221 | `A B C D E` |
| `inspect_evals/commonsense_qa` | `inspect_ai/choice` | echo | 0 | 1221 | `Eating is part of living, but your body doesn't use it all a` |
| `inspect_evals/commonsense_qa` | `inspect_ai/choice` | boilerplate | 0 | 1221 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/commonsense_qa` | `inspect_ai/choice` | format_only | 239 | 1221 | `ANSWER: A` |
| `inspect_evals/commonsense_qa` | `inspect_ai/choice` | majority | 255 | 1221 | `ANSWER: B` |
| `inspect_evals/commonsense_qa` | `inspect_ai/choice` | uniform | 1225 | 6105 | `ANSWER: D` |
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
| `inspect_evals/hellaswag` | `inspect_ai/choice` | empty | 0 | 10042 | `` |
| `inspect_evals/hellaswag` | `inspect_ai/choice` | whitespace | 0 | 10042 | ` ` |
| `inspect_evals/hellaswag` | `inspect_ai/choice` | refusal | 0 | 10042 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/hellaswag` | `inspect_ai/choice` | all_labels | 0 | 10042 | `ANSWER: C, A, B, D` |
| `inspect_evals/hellaswag` | `inspect_ai/choice` | all_letters | 0 | 10042 | `A B C D E` |
| `inspect_evals/hellaswag` | `inspect_ai/choice` | echo | 0 | 10042 | `A leaf is floating through the murky ocean water. A group of` |
| `inspect_evals/hellaswag` | `inspect_ai/choice` | boilerplate | 0 | 10042 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/hellaswag` | `inspect_ai/choice` | format_only | 2515 | 10042 | `ANSWER: A` |
| `inspect_evals/hellaswag` | `inspect_ai/choice` | majority | 2584 | 10042 | `ANSWER: C` |
| `inspect_evals/hellaswag` | `inspect_ai/choice` | uniform | 12426 | 50210 | `ANSWER: C` |
| `inspect_evals/lab_bench_cloning_scenarios` | `inspect_evals/precision_choice` | empty | 0 | 33 | `` |
| `inspect_evals/lab_bench_cloning_scenarios` | `inspect_evals/precision_choice` | whitespace | 0 | 33 | ` ` |
| `inspect_evals/lab_bench_cloning_scenarios` | `inspect_evals/precision_choice` | refusal | 0 | 33 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/lab_bench_cloning_scenarios` | `inspect_evals/precision_choice` | all_labels | 0 | 33 | `ANSWER: E, C, D, A, B, F` |
| `inspect_evals/lab_bench_cloning_scenarios` | `inspect_evals/precision_choice` | all_letters | 0 | 33 | `A B C D E` |
| `inspect_evals/lab_bench_cloning_scenarios` | `inspect_evals/precision_choice` | echo | 0 | 33 | `I want to clone mScarlet into pAAV CAG GFP, in place of the ` |
| `inspect_evals/lab_bench_cloning_scenarios` | `inspect_evals/precision_choice` | boilerplate | 0 | 33 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/lab_bench_cloning_scenarios` | `inspect_evals/precision_choice` | format_only | 5 | 33 | `ANSWER: A` |
| `inspect_evals/lab_bench_cloning_scenarios` | `inspect_evals/precision_choice` | majority | 9 | 33 | `ANSWER: E` |
| `inspect_evals/lab_bench_cloning_scenarios` | `inspect_evals/precision_choice` | uniform | 39 | 165 | `ANSWER: A` |
| `inspect_evals/lab_bench_dbqa` | `inspect_evals/precision_choice` | empty | 0 | 520 | `` |
| `inspect_evals/lab_bench_dbqa` | `inspect_evals/precision_choice` | whitespace | 0 | 520 | ` ` |
| `inspect_evals/lab_bench_dbqa` | `inspect_evals/precision_choice` | refusal | 0 | 520 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/lab_bench_dbqa` | `inspect_evals/precision_choice` | all_labels | 0 | 520 | `ANSWER: A, C, E, B, D` |
| `inspect_evals/lab_bench_dbqa` | `inspect_evals/precision_choice` | all_letters | 0 | 520 | `A B C D E` |
| `inspect_evals/lab_bench_dbqa` | `inspect_evals/precision_choice` | echo | 0 | 520 | `Which of the following genes is most likely contained in the` |
| `inspect_evals/lab_bench_dbqa` | `inspect_evals/precision_choice` | boilerplate | 0 | 520 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/lab_bench_dbqa` | `inspect_evals/precision_choice` | format_only | 120 | 520 | `ANSWER: A` |
| `inspect_evals/lab_bench_dbqa` | `inspect_evals/precision_choice` | majority | 120 | 520 | `ANSWER: A` |
| `inspect_evals/lab_bench_dbqa` | `inspect_evals/precision_choice` | uniform | 495 | 2600 | `ANSWER: D` |
| `inspect_evals/lab_bench_figqa` | `inspect_evals/precision_choice` | empty | 0 | 181 | `` |
| `inspect_evals/lab_bench_figqa` | `inspect_evals/precision_choice` | whitespace | 0 | 181 | ` ` |
| `inspect_evals/lab_bench_figqa` | `inspect_evals/precision_choice` | refusal | 0 | 181 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/lab_bench_figqa` | `inspect_evals/precision_choice` | all_labels | 0 | 181 | `ANSWER: D, A, E, C, B, F, G, H` |
| `inspect_evals/lab_bench_figqa` | `inspect_evals/precision_choice` | all_letters | 0 | 181 | `A B C D E` |
| `inspect_evals/lab_bench_figqa` | `inspect_evals/precision_choice` | echo | 0 | 181 | `Which of the following summarizes the data presented in figu` |
| `inspect_evals/lab_bench_figqa` | `inspect_evals/precision_choice` | boilerplate | 0 | 181 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/lab_bench_figqa` | `inspect_evals/precision_choice` | format_only | 33 | 181 | `ANSWER: A` |
| `inspect_evals/lab_bench_figqa` | `inspect_evals/precision_choice` | majority | 35 | 181 | `ANSWER: D` |
| `inspect_evals/lab_bench_figqa` | `inspect_evals/precision_choice` | uniform | 125 | 905 | `ANSWER: E` |
| `inspect_evals/lab_bench_litqa` | `inspect_evals/precision_choice` | empty | 0 | 199 | `` |
| `inspect_evals/lab_bench_litqa` | `inspect_evals/precision_choice` | whitespace | 0 | 199 | ` ` |
| `inspect_evals/lab_bench_litqa` | `inspect_evals/precision_choice` | refusal | 0 | 199 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/lab_bench_litqa` | `inspect_evals/precision_choice` | all_labels | 0 | 199 | `ANSWER: A, C, E, B, D, G, F, H, J` |
| `inspect_evals/lab_bench_litqa` | `inspect_evals/precision_choice` | all_letters | 0 | 199 | `A B C D E` |
| `inspect_evals/lab_bench_litqa` | `inspect_evals/precision_choice` | echo | 0 | 199 | `Which of the following residues of KBTBD4-PR contributes to ` |
| `inspect_evals/lab_bench_litqa` | `inspect_evals/precision_choice` | boilerplate | 0 | 199 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/lab_bench_litqa` | `inspect_evals/precision_choice` | format_only | 45 | 199 | `ANSWER: A` |
| `inspect_evals/lab_bench_litqa` | `inspect_evals/precision_choice` | majority | 45 | 199 | `ANSWER: A` |
| `inspect_evals/lab_bench_litqa` | `inspect_evals/precision_choice` | uniform | 109 | 995 | `ANSWER: D` |
| `inspect_evals/lab_bench_protocolqa` | `inspect_evals/precision_choice` | empty | 0 | 108 | `` |
| `inspect_evals/lab_bench_protocolqa` | `inspect_evals/precision_choice` | whitespace | 0 | 108 | ` ` |
| `inspect_evals/lab_bench_protocolqa` | `inspect_evals/precision_choice` | refusal | 0 | 108 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/lab_bench_protocolqa` | `inspect_evals/precision_choice` | all_labels | 0 | 108 | `ANSWER: E, A, B, C, D, F` |
| `inspect_evals/lab_bench_protocolqa` | `inspect_evals/precision_choice` | all_letters | 0 | 108 | `A B C D E` |
| `inspect_evals/lab_bench_protocolqa` | `inspect_evals/precision_choice` | echo | 0 | 108 | `Protocol: Protocol for isolating amnion cells from human and` |
| `inspect_evals/lab_bench_protocolqa` | `inspect_evals/precision_choice` | boilerplate | 0 | 108 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/lab_bench_protocolqa` | `inspect_evals/precision_choice` | format_only | 19 | 108 | `ANSWER: A` |
| `inspect_evals/lab_bench_protocolqa` | `inspect_evals/precision_choice` | majority | 29 | 108 | `ANSWER: E` |
| `inspect_evals/lab_bench_protocolqa` | `inspect_evals/precision_choice` | uniform | 86 | 540 | `ANSWER: E` |
| `inspect_evals/lab_bench_seqqa` | `inspect_evals/precision_choice` | empty | 0 | 600 | `` |
| `inspect_evals/lab_bench_seqqa` | `inspect_evals/precision_choice` | whitespace | 0 | 600 | ` ` |
| `inspect_evals/lab_bench_seqqa` | `inspect_evals/precision_choice` | refusal | 0 | 600 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/lab_bench_seqqa` | `inspect_evals/precision_choice` | all_labels | 0 | 600 | `ANSWER: A, D, C, E, B, F` |
| `inspect_evals/lab_bench_seqqa` | `inspect_evals/precision_choice` | all_letters | 0 | 600 | `A B C D E` |
| `inspect_evals/lab_bench_seqqa` | `inspect_evals/precision_choice` | echo | 0 | 600 | `What is the percent GC of the DNA sequence GCAGCATACTGCTAAGG` |
| `inspect_evals/lab_bench_seqqa` | `inspect_evals/precision_choice` | boilerplate | 0 | 600 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/lab_bench_seqqa` | `inspect_evals/precision_choice` | format_only | 136 | 600 | `ANSWER: A` |
| `inspect_evals/lab_bench_seqqa` | `inspect_evals/precision_choice` | majority | 136 | 600 | `ANSWER: A` |
| `inspect_evals/lab_bench_seqqa` | `inspect_evals/precision_choice` | uniform | 521 | 3000 | `ANSWER: C` |
| `inspect_evals/lab_bench_suppqa` | `inspect_evals/precision_choice` | empty | 0 | 82 | `` |
| `inspect_evals/lab_bench_suppqa` | `inspect_evals/precision_choice` | whitespace | 0 | 82 | ` ` |
| `inspect_evals/lab_bench_suppqa` | `inspect_evals/precision_choice` | refusal | 0 | 82 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/lab_bench_suppqa` | `inspect_evals/precision_choice` | all_labels | 0 | 82 | `ANSWER: D, C, A, E, F, B` |
| `inspect_evals/lab_bench_suppqa` | `inspect_evals/precision_choice` | all_letters | 0 | 82 | `A B C D E` |
| `inspect_evals/lab_bench_suppqa` | `inspect_evals/precision_choice` | echo | 0 | 82 | `Paper title: Visualizing SNVs to quantify allele-specific ex` |
| `inspect_evals/lab_bench_suppqa` | `inspect_evals/precision_choice` | boilerplate | 0 | 82 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/lab_bench_suppqa` | `inspect_evals/precision_choice` | format_only | 14 | 82 | `ANSWER: A` |
| `inspect_evals/lab_bench_suppqa` | `inspect_evals/precision_choice` | majority | 26 | 82 | `ANSWER: D` |
| `inspect_evals/lab_bench_suppqa` | `inspect_evals/precision_choice` | uniform | 69 | 410 | `ANSWER: B` |
| `inspect_evals/lab_bench_tableqa` | `inspect_evals/precision_choice` | empty | 0 | 244 | `` |
| `inspect_evals/lab_bench_tableqa` | `inspect_evals/precision_choice` | whitespace | 0 | 244 | ` ` |
| `inspect_evals/lab_bench_tableqa` | `inspect_evals/precision_choice` | refusal | 0 | 244 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/lab_bench_tableqa` | `inspect_evals/precision_choice` | all_labels | 0 | 244 | `ANSWER: A, D, B, E, C, F, G, H` |
| `inspect_evals/lab_bench_tableqa` | `inspect_evals/precision_choice` | all_letters | 0 | 244 | `A B C D E` |
| `inspect_evals/lab_bench_tableqa` | `inspect_evals/precision_choice` | echo | 0 | 244 | `Which AAV type elicits the highest concentration of NAb from` |
| `inspect_evals/lab_bench_tableqa` | `inspect_evals/precision_choice` | boilerplate | 0 | 244 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/lab_bench_tableqa` | `inspect_evals/precision_choice` | format_only | 49 | 244 | `ANSWER: A` |
| `inspect_evals/lab_bench_tableqa` | `inspect_evals/precision_choice` | majority | 49 | 244 | `ANSWER: A` |
| `inspect_evals/lab_bench_tableqa` | `inspect_evals/precision_choice` | uniform | 158 | 1220 | `ANSWER: H` |
| `inspect_evals/macbench` | `inspect_evals/macbench_scorer` | empty | 0 | 1153 | `` |
| `inspect_evals/macbench` | `inspect_evals/macbench_scorer` | whitespace | 0 | 1153 | ` ` |
| `inspect_evals/macbench` | `inspect_evals/macbench_scorer` | refusal | 0 | 1153 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/macbench` | `inspect_evals/macbench_scorer` | all_letters | 0 | 1153 | `A B C D E` |
| `inspect_evals/macbench` | `inspect_evals/macbench_scorer` | echo | 0 | 1153 | `The following is a question about chemistry. Please answer b` |
| `inspect_evals/macbench` | `inspect_evals/macbench_scorer` | boilerplate | 0 | 1153 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/macbench` | `inspect_evals/macbench_scorer` | format_only | 0 | 1153 | `ANSWER: A` |
| `inspect_evals/macbench` | `inspect_evals/macbench_scorer` | majority | 0 | 1153 | `ANSWER: A` |
| `inspect_evals/mmlu_0_shot` | `inspect_ai/choice` | empty | 0 | 13937 | `` |
| `inspect_evals/mmlu_0_shot` | `inspect_ai/choice` | whitespace | 0 | 13937 | ` ` |
| `inspect_evals/mmlu_0_shot` | `inspect_ai/choice` | refusal | 0 | 13937 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/mmlu_0_shot` | `inspect_ai/choice` | all_labels | 0 | 13937 | `ANSWER: D, C, B, A` |
| `inspect_evals/mmlu_0_shot` | `inspect_ai/choice` | all_letters | 0 | 13937 | `A B C D E` |
| `inspect_evals/mmlu_0_shot` | `inspect_ai/choice` | echo | 0 | 13937 | `The European Union (EU) replaced which of the following orga` |
| `inspect_evals/mmlu_0_shot` | `inspect_ai/choice` | boilerplate | 0 | 13937 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/mmlu_0_shot` | `inspect_ai/choice` | format_only | 3204 | 13937 | `ANSWER: A` |
| `inspect_evals/mmlu_0_shot` | `inspect_ai/choice` | majority | 3738 | 13937 | `ANSWER: D` |
| `inspect_evals/mmlu_0_shot` | `inspect_ai/choice` | uniform | 17428 | 69685 | `ANSWER: A` |
| `inspect_evals/mmlu_5_shot` | `inspect_ai/choice` | empty | 0 | 14015 | `` |
| `inspect_evals/mmlu_5_shot` | `inspect_ai/choice` | whitespace | 0 | 14015 | ` ` |
| `inspect_evals/mmlu_5_shot` | `inspect_ai/choice` | refusal | 0 | 14015 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/mmlu_5_shot` | `inspect_ai/choice` | all_labels | 0 | 14015 | `ANSWER: D, C, B, A` |
| `inspect_evals/mmlu_5_shot` | `inspect_ai/choice` | all_letters | 0 | 14015 | `A B C D E` |
| `inspect_evals/mmlu_5_shot` | `inspect_ai/choice` | echo | 3374 | 14015 | `The following are multiple choice questions about philosophy` |
| `inspect_evals/mmlu_5_shot` | `inspect_ai/choice` | boilerplate | 0 | 14015 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/mmlu_5_shot` | `inspect_ai/choice` | format_only | 3219 | 14015 | `ANSWER: A` |
| `inspect_evals/mmlu_5_shot` | `inspect_ai/choice` | majority | 3769 | 14015 | `ANSWER: D` |
| `inspect_evals/mmlu_5_shot` | `inspect_ai/choice` | uniform | 17353 | 70075 | `ANSWER: A` |
| `inspect_evals/mmlu_pro` | `inspect_ai/choice` | empty | 0 | 12032 | `` |
| `inspect_evals/mmlu_pro` | `inspect_ai/choice` | whitespace | 0 | 12032 | ` ` |
| `inspect_evals/mmlu_pro` | `inspect_ai/choice` | refusal | 0 | 12032 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/mmlu_pro` | `inspect_ai/choice` | all_labels | 0 | 12032 | `ANSWER: A, B, D, C, G, E, F, H, I, J` |
| `inspect_evals/mmlu_pro` | `inspect_ai/choice` | all_letters | 0 | 12032 | `A B C D E` |
| `inspect_evals/mmlu_pro` | `inspect_ai/choice` | echo | 0 | 12032 | `Steven Moore purchased a new car for $3,462.20, including ta` |
| `inspect_evals/mmlu_pro` | `inspect_ai/choice` | boilerplate | 0 | 12032 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/mmlu_pro` | `inspect_ai/choice` | format_only | 1403 | 12032 | `ANSWER: A` |
| `inspect_evals/mmlu_pro` | `inspect_ai/choice` | majority | 1403 | 12032 | `ANSWER: A` |
| `inspect_evals/mmlu_pro` | `inspect_ai/choice` | uniform | 5998 | 60160 | `ANSWER: C` |
| `inspect_evals/musr` | `inspect_ai/choice` | empty | 0 | 250 | `` |
| `inspect_evals/musr` | `inspect_ai/choice` | whitespace | 0 | 250 | ` ` |
| `inspect_evals/musr` | `inspect_ai/choice` | refusal | 0 | 250 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/musr` | `inspect_ai/choice` | all_labels | 0 | 250 | `ANSWER: A, B` |
| `inspect_evals/musr` | `inspect_ai/choice` | all_letters | 0 | 250 | `A B C D E` |
| `inspect_evals/musr` | `inspect_ai/choice` | echo | 0 | 250 | `In the isolated serenity of a mountain cabin, tragedy strike` |
| `inspect_evals/musr` | `inspect_ai/choice` | boilerplate | 0 | 250 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/musr` | `inspect_ai/choice` | format_only | 125 | 250 | `ANSWER: A` |
| `inspect_evals/musr` | `inspect_ai/choice` | majority | 125 | 250 | `ANSWER: A` |
| `inspect_evals/musr` | `inspect_ai/choice` | uniform | 635 | 1250 | `ANSWER: B` |
| `inspect_evals/onet_m6` | `inspect_ai/choice` | empty | 0 | 391 | `` |
| `inspect_evals/onet_m6` | `inspect_ai/choice` | whitespace | 0 | 391 | ` ` |
| `inspect_evals/onet_m6` | `inspect_ai/choice` | refusal | 0 | 391 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/onet_m6` | `inspect_ai/choice` | all_labels | 0 | 391 | `ANSWER: C, D, B, A, E` |
| `inspect_evals/onet_m6` | `inspect_ai/choice` | all_letters | 0 | 391 | `A B C D E` |
| `inspect_evals/onet_m6` | `inspect_ai/choice` | echo | 0 | 391 | `คำใดจากกลุ่ม ก. และ กลุ่ม ข. เหมาะจะเติมลงในช่องว่าง (ก) และ` |
| `inspect_evals/onet_m6` | `inspect_ai/choice` | boilerplate | 0 | 391 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/onet_m6` | `inspect_ai/choice` | format_only | 78 | 391 | `ANSWER: A` |
| `inspect_evals/onet_m6` | `inspect_ai/choice` | majority | 83 | 391 | `ANSWER: C` |
| `inspect_evals/onet_m6` | `inspect_ai/choice` | uniform | 381 | 1955 | `ANSWER: D` |
| `inspect_evals/paws` | `inspect_ai/pattern` | empty | 0 | 8000 | `` |
| `inspect_evals/paws` | `inspect_ai/pattern` | whitespace | 0 | 8000 | ` ` |
| `inspect_evals/paws` | `inspect_ai/pattern` | refusal | 0 | 8000 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/paws` | `inspect_ai/pattern` | all_labels | 0 | 8000 | `No Yes` |
| `inspect_evals/paws` | `inspect_ai/pattern` | all_letters | 0 | 8000 | `A B C D E` |
| `inspect_evals/paws` | `inspect_ai/pattern` | echo | 0 | 8000 | `Sentence1: This was a series of nested angular standards , s` |
| `inspect_evals/paws` | `inspect_ai/pattern` | boilerplate | 0 | 8000 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/paws` | `inspect_ai/pattern` | format_only | 0 | 8000 | `ANSWER: A` |
| `inspect_evals/paws` | `inspect_ai/pattern` | majority | 4464 | 8000 | `No` |
| `inspect_evals/paws` | `inspect_ai/pattern` | uniform | 19829 | 40000 | `Yes` |
| `inspect_evals/pre_flight` | `inspect_ai/choice` | empty | 0 | 300 | `` |
| `inspect_evals/pre_flight` | `inspect_ai/choice` | whitespace | 0 | 300 | ` ` |
| `inspect_evals/pre_flight` | `inspect_ai/choice` | refusal | 0 | 300 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/pre_flight` | `inspect_ai/choice` | all_labels | 0 | 300 | `ANSWER: B, C, A, D` |
| `inspect_evals/pre_flight` | `inspect_ai/choice` | all_letters | 0 | 300 | `A B C D E` |
| `inspect_evals/pre_flight` | `inspect_ai/choice` | echo | 0 | 300 | `According to a typical international airport Ground Operatio` |
| `inspect_evals/pre_flight` | `inspect_ai/choice` | boilerplate | 0 | 300 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/pre_flight` | `inspect_ai/choice` | format_only | 73 | 300 | `ANSWER: A` |
| `inspect_evals/pre_flight` | `inspect_ai/choice` | majority | 132 | 300 | `ANSWER: B` |
| `inspect_evals/pre_flight` | `inspect_ai/choice` | uniform | 373 | 1500 | `ANSWER: A` |
| `inspect_evals/pubmedqa` | `inspect_ai/choice` | empty | 0 | 500 | `` |
| `inspect_evals/pubmedqa` | `inspect_ai/choice` | whitespace | 0 | 500 | ` ` |
| `inspect_evals/pubmedqa` | `inspect_ai/choice` | refusal | 0 | 500 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/pubmedqa` | `inspect_ai/choice` | all_labels | 0 | 500 | `ANSWER: A, B, C` |
| `inspect_evals/pubmedqa` | `inspect_ai/choice` | all_letters | 0 | 500 | `A B C D E` |
| `inspect_evals/pubmedqa` | `inspect_ai/choice` | echo | 0 | 500 | `**Context:** Patients transported by helicopter often requir` |
| `inspect_evals/pubmedqa` | `inspect_ai/choice` | boilerplate | 0 | 500 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/pubmedqa` | `inspect_ai/choice` | format_only | 276 | 500 | `ANSWER: A` |
| `inspect_evals/pubmedqa` | `inspect_ai/choice` | majority | 276 | 500 | `ANSWER: A` |
| `inspect_evals/pubmedqa` | `inspect_ai/choice` | uniform | 870 | 2500 | `ANSWER: C` |
| `inspect_evals/race_h` | `inspect_ai/choice` | empty | 0 | 3498 | `` |
| `inspect_evals/race_h` | `inspect_ai/choice` | whitespace | 0 | 3498 | ` ` |
| `inspect_evals/race_h` | `inspect_ai/choice` | refusal | 0 | 3498 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/race_h` | `inspect_ai/choice` | all_labels | 0 | 3498 | `ANSWER: C, B, D, A` |
| `inspect_evals/race_h` | `inspect_ai/choice` | all_letters | 0 | 3498 | `A B C D E` |
| `inspect_evals/race_h` | `inspect_ai/choice` | echo | 0 | 3498 | `For a long time now, I've been fascinated by common phrases ` |
| `inspect_evals/race_h` | `inspect_ai/choice` | boilerplate | 0 | 3498 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/race_h` | `inspect_ai/choice` | format_only | 754 | 3498 | `ANSWER: A` |
| `inspect_evals/race_h` | `inspect_ai/choice` | majority | 950 | 3498 | `ANSWER: C` |
| `inspect_evals/race_h` | `inspect_ai/choice` | uniform | 4377 | 17490 | `ANSWER: B` |
| `inspect_evals/sec_qa_v1` | `inspect_ai/choice` | empty | 0 | 110 | `` |
| `inspect_evals/sec_qa_v1` | `inspect_ai/choice` | whitespace | 0 | 110 | ` ` |
| `inspect_evals/sec_qa_v1` | `inspect_ai/choice` | refusal | 0 | 110 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/sec_qa_v1` | `inspect_ai/choice` | all_labels | 0 | 110 | `ANSWER: B, D, C, A` |
| `inspect_evals/sec_qa_v1` | `inspect_ai/choice` | all_letters | 0 | 110 | `A B C D E` |
| `inspect_evals/sec_qa_v1` | `inspect_ai/choice` | echo | 0 | 110 | `Why is cryptography essential in the field of security?` |
| `inspect_evals/sec_qa_v1` | `inspect_ai/choice` | boilerplate | 0 | 110 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/sec_qa_v1` | `inspect_ai/choice` | format_only | 21 | 110 | `ANSWER: A` |
| `inspect_evals/sec_qa_v1` | `inspect_ai/choice` | majority | 32 | 110 | `ANSWER: B` |
| `inspect_evals/sec_qa_v1` | `inspect_ai/choice` | uniform | 136 | 550 | `ANSWER: B` |
| `inspect_evals/sec_qa_v1_5_shot` | `inspect_ai/choice` | empty | 0 | 110 | `` |
| `inspect_evals/sec_qa_v1_5_shot` | `inspect_ai/choice` | whitespace | 0 | 110 | ` ` |
| `inspect_evals/sec_qa_v1_5_shot` | `inspect_ai/choice` | refusal | 0 | 110 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/sec_qa_v1_5_shot` | `inspect_ai/choice` | all_labels | 0 | 110 | `ANSWER: B, D, C, A` |
| `inspect_evals/sec_qa_v1_5_shot` | `inspect_ai/choice` | all_letters | 0 | 110 | `A B C D E` |
| `inspect_evals/sec_qa_v1_5_shot` | `inspect_ai/choice` | echo | 0 | 110 | `Why is cryptography essential in the field of security?` |
| `inspect_evals/sec_qa_v1_5_shot` | `inspect_ai/choice` | boilerplate | 0 | 110 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/sec_qa_v1_5_shot` | `inspect_ai/choice` | format_only | 21 | 110 | `ANSWER: A` |
| `inspect_evals/sec_qa_v1_5_shot` | `inspect_ai/choice` | majority | 32 | 110 | `ANSWER: B` |
| `inspect_evals/sec_qa_v1_5_shot` | `inspect_ai/choice` | uniform | 136 | 550 | `ANSWER: B` |
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
| `inspect_evals/sec_qa_v2_5_shot` | `inspect_ai/choice` | empty | 0 | 100 | `` |
| `inspect_evals/sec_qa_v2_5_shot` | `inspect_ai/choice` | whitespace | 0 | 100 | ` ` |
| `inspect_evals/sec_qa_v2_5_shot` | `inspect_ai/choice` | refusal | 0 | 100 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/sec_qa_v2_5_shot` | `inspect_ai/choice` | all_labels | 0 | 100 | `ANSWER: B, C, A, D` |
| `inspect_evals/sec_qa_v2_5_shot` | `inspect_ai/choice` | all_letters | 0 | 100 | `A B C D E` |
| `inspect_evals/sec_qa_v2_5_shot` | `inspect_ai/choice` | echo | 0 | 100 | `When implementing secure application development practices, ` |
| `inspect_evals/sec_qa_v2_5_shot` | `inspect_ai/choice` | boilerplate | 0 | 100 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/sec_qa_v2_5_shot` | `inspect_ai/choice` | format_only | 21 | 100 | `ANSWER: A` |
| `inspect_evals/sec_qa_v2_5_shot` | `inspect_ai/choice` | majority | 31 | 100 | `ANSWER: B` |
| `inspect_evals/sec_qa_v2_5_shot` | `inspect_ai/choice` | uniform | 113 | 500 | `ANSWER: B` |
| `inspect_evals/squad` | `inspect_ai/exact` | empty | 3 | 11873 | `` |
| `inspect_evals/squad` | `inspect_ai/exact` | whitespace | 3 | 11873 | ` ` |
| `inspect_evals/squad` | `inspect_ai/exact` | refusal | 0 | 11873 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/squad` | `inspect_ai/exact` | all_letters | 0 | 11873 | `A B C D E` |
| `inspect_evals/squad` | `inspect_ai/exact` | echo | 0 | 11873 | `Context: The Normans (Norman: Nourmands; French: Normands; L` |
| `inspect_evals/squad` | `inspect_ai/exact` | boilerplate | 0 | 11873 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/squad` | `inspect_ai/exact` | format_only | 0 | 11873 | `ANSWER: A` |
| `inspect_evals/squad` | `inspect_ai/exact` | majority | 5945 | 11873 | `unanswerable` |
| `inspect_evals/squad` | `inspect_ai/f1` | empty | 3 | 11873 | `` |
| `inspect_evals/squad` | `inspect_ai/f1` | whitespace | 3 | 11873 | ` ` |
| `inspect_evals/squad` | `inspect_ai/f1` | refusal | 0 | 11873 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/squad` | `inspect_ai/f1` | all_letters | 0 | 11873 | `A B C D E` |
| `inspect_evals/squad` | `inspect_ai/f1` | echo | 0 | 11873 | `Context: The Normans (Norman: Nourmands; French: Normands; L` |
| `inspect_evals/squad` | `inspect_ai/f1` | boilerplate | 0 | 11873 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/squad` | `inspect_ai/f1` | format_only | 0 | 11873 | `ANSWER: A` |
| `inspect_evals/squad` | `inspect_ai/f1` | majority | 5945 | 11873 | `unanswerable` |
| `inspect_evals/truthfulqa` | `inspect_ai/choice` | empty | 0 | 817 | `` |
| `inspect_evals/truthfulqa` | `inspect_ai/choice` | whitespace | 0 | 817 | ` ` |
| `inspect_evals/truthfulqa` | `inspect_ai/choice` | refusal | 0 | 817 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/truthfulqa` | `inspect_ai/choice` | all_labels | 0 | 817 | `ANSWER: A, B, C, D, E, F, G, H, I, J` |
| `inspect_evals/truthfulqa` | `inspect_ai/choice` | all_letters | 0 | 817 | `A B C D E` |
| `inspect_evals/truthfulqa` | `inspect_ai/choice` | echo | 0 | 817 | `Are there wizards living in the West Country?` |
| `inspect_evals/truthfulqa` | `inspect_ai/choice` | boilerplate | 0 | 817 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/truthfulqa` | `inspect_ai/choice` | format_only | 203 | 817 | `ANSWER: A` |
| `inspect_evals/truthfulqa` | `inspect_ai/choice` | majority | 203 | 817 | `ANSWER: A` |
| `inspect_evals/truthfulqa` | `inspect_ai/choice` | uniform | 430 | 4085 | `ANSWER: G` |
| `inspect_evals/vstar_bench_attribute_recognition` | `inspect_ai/choice` | empty | 0 | 115 | `` |
| `inspect_evals/vstar_bench_attribute_recognition` | `inspect_ai/choice` | whitespace | 0 | 115 | ` ` |
| `inspect_evals/vstar_bench_attribute_recognition` | `inspect_ai/choice` | refusal | 0 | 115 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/vstar_bench_attribute_recognition` | `inspect_ai/choice` | all_labels | 0 | 115 | `ANSWER: A, B, C, D` |
| `inspect_evals/vstar_bench_attribute_recognition` | `inspect_ai/choice` | all_letters | 0 | 115 | `A B C D E` |
| `inspect_evals/vstar_bench_attribute_recognition` | `inspect_ai/choice` | echo | 0 | 115 | `What is the material of the glove?` |
| `inspect_evals/vstar_bench_attribute_recognition` | `inspect_ai/choice` | boilerplate | 0 | 115 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/vstar_bench_attribute_recognition` | `inspect_ai/choice` | format_only | 34 | 115 | `ANSWER: A` |
| `inspect_evals/vstar_bench_attribute_recognition` | `inspect_ai/choice` | majority | 34 | 115 | `ANSWER: A` |
| `inspect_evals/vstar_bench_attribute_recognition` | `inspect_ai/choice` | uniform | 138 | 575 | `ANSWER: B` |
| `inspect_evals/vstar_bench_spatial_relationship_reasoning` | `inspect_ai/choice` | empty | 0 | 76 | `` |
| `inspect_evals/vstar_bench_spatial_relationship_reasoning` | `inspect_ai/choice` | whitespace | 0 | 76 | ` ` |
| `inspect_evals/vstar_bench_spatial_relationship_reasoning` | `inspect_ai/choice` | refusal | 0 | 76 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/vstar_bench_spatial_relationship_reasoning` | `inspect_ai/choice` | all_labels | 0 | 76 | `ANSWER: B, A` |
| `inspect_evals/vstar_bench_spatial_relationship_reasoning` | `inspect_ai/choice` | all_letters | 0 | 76 | `A B C D E` |
| `inspect_evals/vstar_bench_spatial_relationship_reasoning` | `inspect_ai/choice` | echo | 0 | 76 | `Is the telephone on the left or right side of the hand lamp?` |
| `inspect_evals/vstar_bench_spatial_relationship_reasoning` | `inspect_ai/choice` | boilerplate | 0 | 76 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/vstar_bench_spatial_relationship_reasoning` | `inspect_ai/choice` | format_only | 37 | 76 | `ANSWER: A` |
| `inspect_evals/vstar_bench_spatial_relationship_reasoning` | `inspect_ai/choice` | majority | 39 | 76 | `ANSWER: B` |
| `inspect_evals/vstar_bench_spatial_relationship_reasoning` | `inspect_ai/choice` | uniform | 180 | 380 | `ANSWER: B` |
| `inspect_evals/winogrande` | `inspect_ai/choice` | empty | 0 | 1267 | `` |
| `inspect_evals/winogrande` | `inspect_ai/choice` | whitespace | 0 | 1267 | ` ` |
| `inspect_evals/winogrande` | `inspect_ai/choice` | refusal | 0 | 1267 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/winogrande` | `inspect_ai/choice` | all_labels | 0 | 1267 | `ANSWER: B, A` |
| `inspect_evals/winogrande` | `inspect_ai/choice` | all_letters | 0 | 1267 | `A B C D E` |
| `inspect_evals/winogrande` | `inspect_ai/choice` | echo | 0 | 1267 | `Sentence: Kyle was in a lot of pain after running the marath` |
| `inspect_evals/winogrande` | `inspect_ai/choice` | boilerplate | 0 | 1267 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/winogrande` | `inspect_ai/choice` | format_only | 628 | 1267 | `ANSWER: A` |
| `inspect_evals/winogrande` | `inspect_ai/choice` | majority | 639 | 1267 | `ANSWER: B` |
| `inspect_evals/winogrande` | `inspect_ai/choice` | uniform | 3170 | 6335 | `ANSWER: B` |
| `inspect_evals/wmdp_bio` | `inspect_ai/choice` | empty | 0 | 1273 | `` |
| `inspect_evals/wmdp_bio` | `inspect_ai/choice` | whitespace | 0 | 1273 | ` ` |
| `inspect_evals/wmdp_bio` | `inspect_ai/choice` | refusal | 0 | 1273 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/wmdp_bio` | `inspect_ai/choice` | all_labels | 0 | 1273 | `ANSWER: C, B, A, D` |
| `inspect_evals/wmdp_bio` | `inspect_ai/choice` | all_letters | 0 | 1273 | `A B C D E` |
| `inspect_evals/wmdp_bio` | `inspect_ai/choice` | echo | 0 | 1273 | `You want to store infectious 1918 influenza samples for abou` |
| `inspect_evals/wmdp_bio` | `inspect_ai/choice` | boilerplate | 0 | 1273 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/wmdp_bio` | `inspect_ai/choice` | format_only | 314 | 1273 | `ANSWER: A` |
| `inspect_evals/wmdp_bio` | `inspect_ai/choice` | majority | 338 | 1273 | `ANSWER: C` |
| `inspect_evals/wmdp_bio` | `inspect_ai/choice` | uniform | 1574 | 6365 | `ANSWER: D` |
| `inspect_evals/wmdp_chem` | `inspect_ai/choice` | empty | 0 | 408 | `` |
| `inspect_evals/wmdp_chem` | `inspect_ai/choice` | whitespace | 0 | 408 | ` ` |
| `inspect_evals/wmdp_chem` | `inspect_ai/choice` | refusal | 0 | 408 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/wmdp_chem` | `inspect_ai/choice` | all_labels | 0 | 408 | `ANSWER: D, B, C, A` |
| `inspect_evals/wmdp_chem` | `inspect_ai/choice` | all_letters | 0 | 408 | `A B C D E` |
| `inspect_evals/wmdp_chem` | `inspect_ai/choice` | echo | 0 | 408 | `Which is a schedule 1 chemical weapon?` |
| `inspect_evals/wmdp_chem` | `inspect_ai/choice` | boilerplate | 0 | 408 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/wmdp_chem` | `inspect_ai/choice` | format_only | 96 | 408 | `ANSWER: A` |
| `inspect_evals/wmdp_chem` | `inspect_ai/choice` | majority | 108 | 408 | `ANSWER: D` |
| `inspect_evals/wmdp_chem` | `inspect_ai/choice` | uniform | 535 | 2040 | `ANSWER: B` |
| `inspect_evals/wmdp_cyber` | `inspect_ai/choice` | empty | 0 | 1987 | `` |
| `inspect_evals/wmdp_cyber` | `inspect_ai/choice` | whitespace | 0 | 1987 | ` ` |
| `inspect_evals/wmdp_cyber` | `inspect_ai/choice` | refusal | 0 | 1987 | `I'm sorry, but I can't help with that.` |
| `inspect_evals/wmdp_cyber` | `inspect_ai/choice` | all_labels | 0 | 1987 | `ANSWER: A, C, D, B` |
| `inspect_evals/wmdp_cyber` | `inspect_ai/choice` | all_letters | 0 | 1987 | `A B C D E` |
| `inspect_evals/wmdp_cyber` | `inspect_ai/choice` | echo | 0 | 1987 | `I captured a network packet of type '<ARP Packet>' with the ` |
| `inspect_evals/wmdp_cyber` | `inspect_ai/choice` | boilerplate | 0 | 1987 | `Thank you for the question. This is an interesting problem a` |
| `inspect_evals/wmdp_cyber` | `inspect_ai/choice` | format_only | 528 | 1987 | `ANSWER: A` |
| `inspect_evals/wmdp_cyber` | `inspect_ai/choice` | majority | 528 | 1987 | `ANSWER: A` |
| `inspect_evals/wmdp_cyber` | `inspect_ai/choice` | uniform | 2484 | 9935 | `ANSWER: C` |

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
