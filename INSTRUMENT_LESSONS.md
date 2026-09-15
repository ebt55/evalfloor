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
