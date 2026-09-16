# Instrument lessons

Every defect in the measuring instrument, when it was caught, and what it
invalidated. Defects are logged here rather than quietly fixed, because the
history of what the instrument got wrong is what tells a reader how much to trust
what it now says.

One row per defect. Newest last.

---

## 001 -- `choice()` tasks were not being driven at all

* **Caught** 2026-09-15, by the first smoke sweep, on `inspect_evals/sec_qa_v2`.
* **Symptom** the task reported as FLAGGED by all eight content-free members,
  each at 0.0 per cent, with a majority baseline of 0.0 per cent.
* **Cause** `choice()` does not read the completion text. It reads which entries
  of `state.choices` are marked correct, and those marks are set by the
  `multiple_choice()` solver *after* generation, by parsing `ANSWER: X` out of
  the completion. The driver built a `TaskState` and called the scorer without
  that step, so no choice was ever marked and everything scored zero.
* **What it invalidated** every multiple-choice row. Sixteen of the twenty tasks
  in the first sweep use `choice()`, so had this shipped, the headline would have
  been roughly "16 of 20 flagged" and every one of those sixteen would have been
  an artifact of the harness.
* **Fix** `drive.build_state` performs the same parse-and-mark step Inspect's own
  solver performs, when the sample has choices.
* **Pinned by** `tests/test_controls.py::test_multiple_choice_tasks_are_actually_driven`.

## 002 -- the flag rule fired on `0 >= 0`

* **Caught** 2026-09-15, same sweep, same task. Found because defect 001 made it
  visible; it is a separate defect and would have survived the fix to 001 in any
  task the harness could not drive for some other reason.
* **Symptom** a task where nothing scored at all was reported as flagged by the
  whole battery.
* **Cause** the flag rule read "content-free member at or above `majority`". When
  a scorer cannot be driven, `majority` is 0 and every member trivially satisfies
  `0 >= 0`.
* **What it invalidated** any row for a task the harness could not drive. It
  turned instrument failures into findings, which is the worst direction for an
  audit to fail in.
* **Fix** the rule now requires the member to score strictly above zero as well
  as at or above `majority`. A member that scores nothing has not reached any
  floor. Recorded in `PREREGISTRATION.draft.md` section 4.
* **Pinned by** `tests/test_controls.py::test_a_task_where_nothing_scores_is_not_flagged`.

## 003 -- reference baselines could not parse on multiple-choice tasks

* **Caught** 2026-09-15, while fixing 001.
* **Symptom** would have shown as a `majority` baseline far below the real
  majority-class rate on every `choice()` task.
* **Cause** the `majority` baseline emitted the bare modal target, e.g. `"C"`.
  On a multiple-choice task that does not match `ANSWER: X` and so selects
  nothing, scoring 0. A chance line that cannot parse is not a chance line.
* **What it invalidated** the comparison the entire flag rule rests on, for every
  multiple-choice task.
* **Fix** superseded the same day by the general rendering rule (see below).
  Initially only the two reference baselines were reformatted. That was a
  special case, and special cases in a measurement definition are where bias
  hides.
* **Pinned by** `tests/test_controls.py::test_multiple_choice_tasks_are_actually_driven`.

## 004 -- a shuffled dataset made every limited sweep non-reproducible

* **Caught** 2026-09-15, by writing the determinism control as a test over the
  real smoke set rather than trusting the single manual comparison done earlier.
* **Symptom** two sweeps of the same five tasks with `--limit 200` produced
  different digests. Three of the five were stable; `paws` and `boolq` were not.
* **Cause** not this harness. Both evals declare `shuffle: bool = True` and do
  not seed the shuffle, so two calls to the same task function return the same
  samples in a different order. Any `--limit` then takes a **different subset**
  each run.
* **What it invalidated** nothing published, because the manual determinism
  check on 2026-09-15 happened to compare two *unlimited* sweeps, where every
  sample is scored either way and the counts agree regardless of order. The
  defect would have appeared the moment a sampled arm was used -- which is
  exactly what the model-graded arm will need, since it is capped at 100 samples
  per task.
* **Fix** `drive.task_samples` sorts samples by id before applying any limit.
  Sorting changes nothing about a full sweep and makes a limited one
  reproducible.
* **Lesson worth more than the fix** the earlier "determinism control passes"
  claim was true and not enough. One manual comparison of one configuration is
  not a control; the control is the test that runs both configurations.
* **Pinned by**
  `tests/test_sweep_controls.py::test_shuffled_datasets_still_yield_a_stable_limited_subset`
  and `::test_two_sweeps_of_the_smoke_set_have_the_same_digest`.

## 005 -- rendering generalised, replacing the special case in 003

* **Caught** 2026-09-15, on review of the fix for 003.
* **Symptom** none yet; this is a design defect rather than a wrong number.
  Fixing 003 by reformatting only `majority` and `uniform` left the battery with
  two members written in the task's answer template and six written outside it,
  for no reason a reader could check.
* **Cause** the fix treated a general problem -- a semantic value has to be
  written down somehow -- as a special case about baselines.
* **Fix** every member is now defined semantically and rendered in the task's
  declared answer template when it declares one, and **both** the raw and the
  rendered arm are scored and published. The flag rule reads the rendered arm.
  Members whose value is not label-valued (`empty`, `whitespace`, `refusal`,
  `all_letters`, `echo`, `boilerplate`) are never templated in either arm.
* **What it changed in the numbers** on `paws`, nothing: it declares no answer
  template, so its two arms are identical by construction and the 8000/8000
  anchor cannot have come from a template choice. That is now asserted as a
  test. On multiple-choice tasks it makes `all_labels` render as
  `ANSWER: A, B, C, D`, which scores **0.000**, because `parse_answers` rejects
  a multi-option answer to a single-answer question. `choice()` is genuinely
  tight against "name every label" -- a real negative result that the earlier
  special-cased version could not have produced.
* **Pinned by** `tests/test_paws_regression.py::test_paws_declares_no_answer_template_so_the_arms_coincide`.

## 006 -- an ungradeable grader response was about to be reported as a zero

* **Caught** 2026-09-15, by the first graded smoke run, on `inspect_evals/coconot`.
* **Symptom** two of them, in sequence. First the task reported every member at
  `0.0%`; then, once the grader was actually reaching the scorer, every member
  reported `nan%`.
* **Cause** two separate defects wearing the same mask.
  1. `coconot` takes its judge as a **task parameter** (`grader`, defaulting to
     a hard-coded provider model), so setting `INSPECT_EVAL_MODEL` did not
     redirect it. Every call failed on a missing provider dependency, and the
     arm reported `0.0%` -- a floor that had never been measured.
  2. With the judge injected properly, `model_graded_qa` returned a **non-finite
     score** for each call: the grader answered, but emitted nothing matching the
     grade pattern, so the scorer's value was `NaN`. `NaN` propagates through a
     mean silently and compares `False` against every threshold, so the flag rule
     would have quietly declined to flag anything, for ever, with no error.
* **What it invalidated** nothing published -- this was the first graded run and
  it was a mock. But the shape is the exact failure this project exists to find:
  a number that looks like a measured floor and is not one.
* **Fix**, three parts.
  - `graded.grader_task_args` introspects each task's signature and injects the
    judge through whatever grader parameter it declares; when a task declares
    none, `grader_injected_via` is empty and the report prints
    "NOT REDIRECTABLE" rather than pretending the cheap judge was used.
  - A non-finite score is now its own outcome, `ungradeable`, counted separately
    and **excluded from the denominator**. It is not an error, not a refusal, and
    explicitly not a zero.
  - `ArmResult.mean` can no longer return a non-finite value, and a task where
    nothing scored is marked `nothing_scored`, printed as `NO RESULT`, and kept
    out of the flag-rate denominator entirely.
* **Lesson** the deterministic arm made "scored zero" and "never scored" look
  alike because with a pure scorer they almost never diverge. With a model in the
  loop they diverge constantly, and every one of the three outcomes -- graded,
  refused, ungradeable -- needs its own column.
* **Pinned by** `tests/test_graded.py`.

## 007 -- an eval's own grade vocabulary was being converted to zero

* **Caught** 2026-09-15, by the first real graded run on `inspect_evals/coconot`.
* **Symptom** the run printed `Unable to convert value to float: neither` 140
  times and reported every battery member at 0.0 per cent. A warning per call
  and a floor of zero, which reads as a clean result rather than a broken one.
* **Cause** graded evals define their own grade vocabularies. `coconot` answers
  **ACCEPTABLE / UNACCEPTABLE / NEITHER**, and Inspect's generic
  `value_to_float()` knows only `C` / `P` / `I` / `N`. Handed anything else it
  logs a warning and returns **0.0**, so all three verdicts became zero.
* **What it invalidated** every graded number on that run, and in the worst
  available direction. `coconot`'s own converter maps **`unacceptable` -> 1.0**
  (`coconot.py:209-211`), because in that subset UNACCEPTABLE means the model
  complied with a prompt it should have declined, and that is the outcome the
  eval scores. Zeroing it silently discarded the 14 verdicts of the 140 that the
  eval itself credits, and so **understated the floor** -- in an audit built to
  find floors that are higher than they look, that is the worst way to fail.
* **Fix** the eval's converter is not reachable from the built `Task` -- Inspect
  flattens `epochs` to an int and drops the reducer that held it -- so the
  mapping cannot be read off the object at run time. It is therefore a judgement
  call, and judgement calls in this project live in a committed file that quotes
  the source line they came from: `verdict_maps.jsonl`, one row per eval, loaded
  mechanically, and rejected at load time if a row carries no `source`. A
  verdict with **no** mapping is never coerced to 0.0 -- it is recorded verbatim
  as an `unmapped_verdict`, excluded from the denominator, and its distribution
  printed in the matrix.
* **Lesson** a value a scorer cannot read is not a value of zero, and a
  converter that answers 0.0 instead of declining collapses the first into the
  second at every call site at once. The generic path has to decline; only a
  committed, sourced mapping may supply a number.
* **Pinned by**
  `tests/test_graded.py::test_a_verdict_in_an_evals_own_vocabulary_is_never_silently_zeroed`
  and `::test_every_verdict_map_quotes_the_source_line_it_came_from`.

## 008 -- the provider pin was requested on a channel that was overwritten

* **Caught** 2026-09-16, by the task of capturing which provider actually served
  the second grader. Nothing failed; the defect was found by asking for a fact
  the instrument had never been asked to record.
* **Symptom** none visible. Every run printed, and every file repeated, that
  `openrouter/z-ai/glm-5.3-flash` was "pinned to DeepInfra". No results file
  recorded which provider served any call, so there was nothing that could
  contradict the claim -- and the request itself was being discarded in silence,
  with no error and no warning from either side.
* **Cause** `graded.judge_model_args` sent the pin as
  `extra_body={"provider": {"order": ["DeepInfra"], "allow_fallbacks": false}}`.
  Inspect's OpenRouter provider collects `provider` as a **model argument** and
  builds `extra_body` itself (`openrouter.py`, `collect_model_arg`), so the
  `extra_body` handed in was overwritten before the request went out. The pin
  was the right value on the wrong channel, which is indistinguishable from no
  pin at all except by looking at the response.
* **What it invalidated** the judge-disagreement figure published in commit
  255eb3a -- 10 of 105 = 9.5 per cent [5.3, 16.6] -- and the "pinned rate" cost
  line quoted beside it. Neither is wrong as a measurement; both were measured
  under routing that was never recorded, so neither is the pinned-DeepInfra
  measurement the surrounding text claimed it was. The price per second-grader
  call may have been the canonical rate, about double the pinned one.
  Re-measured with the pin in the channel that client reads:
  **13 of 111 = 11.7 per cent [7.0, 19.0]**. The two arms differ in serving
  provider and in ordinary run-to-run variation of a non-deterministic grader at
  once, so the move is not evidence that routing changed the rate.
* **Fix**, four parts.
  - The pin is passed as a model arg, which is what that client reads.
  - `graded.probe_openrouter_routing` asks OpenRouter with the identical pin and
    reads the top-level `provider` field off the response. Inspect does not
    surface that field on `ModelOutput`, so it cannot be read off the grading
    calls the harness already makes.
  - `served_provider` is recorded on every cache row, every refusal row, the
    `TaskRun`, the `TaskFloor`, the CLI printout, the disagreement block and the
    report table. It reads `unreported` where it could not be read, and is
    **never** back-filled from the pin. On this smoke 136 of 140 second-grader
    rows carry `DeepInfra` and 4 carry `unreported`, because the probe that
    accompanied those 4 lost the race described below. Four holes in the record
    are published as four holes, not as four DeepInfra calls.
  - The routing note counts the rows that recorded a provider, not the rows that
    produced a usable score. A grader that answered with an ungradeable verdict
    was still served by somebody; a call that errored was not served at all.
* **Second defect, found by the fix** the probe asked once. DeepInfra's shared
  pool returns a transient `429 engine_overloaded` often enough to matter:
  measured 2026-09-16, two of twelve single-shot probes returned a provider name
  and the other ten returned 429, while the four grading calls made alongside
  the failures went through normally. One attempt would
  therefore have written `unreported` for a pin that was in fact honoured --
  failing safe, but recording its own absence more often than the answer. The
  probe now retries with backoff before reporting nothing. It still refuses to
  read the provider name out of an error body: a provider that refused a call
  did not serve it.
* **Lesson** a request is not a fact. A configuration line that says "pinned"
  proves nothing about what happened until the response says who served it, and
  the gap between the two can stay invisible indefinitely, because everything
  downstream is quoting the request back rather than the answer. The same
  applies to the fact once it is being read: a measurement taken once, over a
  channel that fails intermittently, records absence as readily as it records
  the answer.
* **Pinned by** `tests/test_graded.py::test_provider_pinning_is_requested`,
  `::test_the_serving_provider_is_recorded_not_inferred` and
  `::test_the_routing_probe_retries_before_reporting_nothing`.
