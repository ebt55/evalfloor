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
* **Fix** `battery.render_reference` emits `ANSWER: <label>` when the sample has
  choices. **Only the two reference baselines are reformatted; content-free
  members never are.** The asymmetry runs in the conservative direction: it
  raises the bar a content-free member has to clear, so it can only reduce the
  flag count, never inflate it.
* **Note** this is open question 8.2 in the preregistration draft. The mirror
  decision -- whether `all_labels` should also be format-aware -- was left
  deliberately unchanged and needs a human decision before the real sweep.
* **Pinned by** `tests/test_controls.py::test_multiple_choice_tasks_are_actually_driven`.
