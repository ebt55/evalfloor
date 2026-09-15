# NOTES

Working log. Pins and why, what was verified first-hand, what failed.
Newest section last. Every claim here is something that was run or fetched, not
something carried over from a plan document.

---

## 2026-09-15 -- day 1

### Upstream status, verified first-hand

Checked with `gh` against `UKGovernmentBEIS/inspect_evals` on 2026-09-15.

| Thing | What the API says |
|---|---|
| Issue [#2331](https://github.com/UKGovernmentBEIS/inspect_evals/issues/2331) | **OPEN**. Opened 2026-08-31T08:53:18Z by **caiotheodoro** (Caio Theodoro). `closedAt: null`. Title: "``paws``: ``includes()`` scorer credits any completion containing both labels -- a constant string scores 100%". Not our issue; credit it, never claim it. |
| PR [#2334](https://github.com/UKGovernmentBEIS/inspect_evals/pull/2334) | **OPEN, not merged**. `mergedAt: null`. Opened 2026-09-01T00:00:21Z by **jkopczyn** (Jacob Kopczynski), branch `includes_hardening`. Touches `paws/paws.py`, `boolq/boolq.py`, both `eval.yaml`s, both READMEs, both test files, plus a new `tests/utils/case_lists.py`. |

One correction to what the plan documents say. The plan says #2334 was "approved
merge-ready Sep 9". What is actually there:

* `gh pr view 2334 --json reviewDecision` returns **`REVIEW_REQUIRED`**, and
  `GET /pulls/2334/reviews` returns an **empty list**. There is no formal GitHub
  approving review on the PR.
* What exists is an **issue comment** dated 2026-09-09T08:27:35Z from
  **MattFisher**, ending "**Verdict: merge-ready.**", reporting that the fix was
  reproduced on the merge base and on the PR head, that reverting the source
  fails 22 of the PR's tests, and that ruff/mypy/changelog/README/eval tests pass
  on the head. It also notes "fork PR so CI has not run".

So: merge-ready in a maintainer's words, in a comment, on 2026-09-09; **not**
approved in GitHub's review state, and **not merged** as of 2026-09-15. The
README says "in flight", which is the accurate phrasing. Do not upgrade it.

### Pins chosen

```
inspect_ai   == 0.3.263
inspect_evals == 0.20.0
```

**Why 0.20.0, and not an older version.** The brief allowed for having to pin
"the last version before the #2334 fix". That turned out to be unnecessary. I
read `src/inspect_evals/paws/paws.py` at each release tag through the GitHub
contents API:

| tag | released | `paws` scorer |
|---|---|---|
| v0.18.0 | 2026-08-20 | `scorer=includes()` |
| v0.19.0 | 2026-08-31 | `scorer=includes()` |
| **v0.20.0** | **2026-09-11** | **`scorer=includes()`** |

v0.20.0 is the latest release on PyPI (uploaded 2026-09-11T14:43:50). The #2334
fix is in **no** release, because the PR is not merged. So the anchor test runs
against the newest published version, which is strictly better than pinning a
stale one: nobody can answer the result with "that was fixed months ago".

**Why inspect_ai 0.3.263.** `inspect_evals` 0.20.0 declares `inspect_ai>=0.3.259`.
0.3.263 (2026-09-04) is the latest release on PyPI and satisfies it. The #2331
reproduction was written against 0.3.260; nothing in the driver depends on the
difference, and pinning the newest compatible version keeps the same "not a
stale bug" property.

**Re-run the whole sweep on any bump.** Mixing versions across rows is not
allowed; `results/` records the pins in every generated file.

### Environment

* Windows 11, Git Bash. `uv` 0.6.0 present, so `uv venv` + `uv pip install`
  (no `python -m venv` fallback needed). Python 3.13.12 in the venv.
* `inspect_evals` 0.20.0 ships **131 eval directories**, **129 `eval.yaml`
  files**, **248 registered tasks** (`registry_find(type == "task")`), and 250
  `@task`-decorated functions found by AST walk. The two extra AST hits are task
  functions not exported through `_registry.py`.
* Hugging Face cache warns that Windows has no symlink support, so the cache
  stores full copies. Disk use is therefore higher than on Linux. Relevant to the
  size cap.

### What the driver does

`drive.py` builds a `TaskState` carrying a `ModelOutput` whose completion is the
battery member, names the model `mockllm/model`, and awaits the task's real
scorer against `Target(sample.target)`. Checked signatures against the installed
`inspect_ai` 0.3.263 rather than guessing: `TaskState.__init__` takes
`(model, sample_id, epoch, input, messages, target=, choices=, output=, ...)`,
and `ModelOutput.from_content(model, content)` is the constructor to use.

Scores are converted with `value_to_float()` and recorded two ways per arm: the
mean over samples the scorer returned a score for, and a strict count of samples
scoring exactly 1.0. The regression test asserts on the strict count.

### First real result -- #2331 reproduced

Full battery over `inspect_evals/paws`, 8000 samples, scorer
`inspect_ai/includes`, on the pins above. No model called; the whole battery took
6.0 s after a 14.6 s dataset download.

| member | correct / n | mean |
|---|---|---|
| empty | 0 / 8000 | 0.0000 |
| whitespace | 0 / 8000 | 0.0000 |
| refusal | 0 / 8000 | 0.0000 |
| **all_labels** | **8000 / 8000** | **1.0000** |
| all_letters | 0 / 8000 | 0.0000 |
| echo | 970 / 8000 | 0.1212 |
| boilerplate | 0 / 8000 | 0.0000 |
| format_only | 0 / 8000 | 0.0000 |
| *majority* | *4464 / 8000* | *0.5580* |
| *uniform* (5 seeds) | -- | *0.4899, 0.4975, 0.4895, 0.4996, 0.5021* |

`all_labels` on `paws` is the constant string **`"No Yes"`** (distinct targets,
ordered by descending frequency then lexicographically, space-joined). It is a
different constant from the `"yesno"` in #2331 and it reaches the same 8000/8000,
which is the point: the result is a property of the scorer, not of the clever
string someone picked.

Two things worth keeping:

1. **The majority line is 0.558, not 0.5.** `paws` test is 55.8% `No`. Computing
   the chance line per task from the dataset, rather than assuming balance, is
   what stops this from being an eyeballed comparison.
2. **`echo` scores 12.1% unprompted.** Echoing the input back scores on 970
   samples because 970 of the paired sentences happen to contain "no" or "yes" as
   a substring somewhere in their text. Nobody designed that; it falls out of
   substring matching over natural language. This is a secondary finding of the
   same shape as #2331 and it was not in the plan.

### Judgement calls made today

* **`all_labels` ordering.** Descending frequency, ties lexicographic, joined by
  a single space. Any order reaches 8000/8000 under `includes()`; a fixed order
  is required so two sweeps are byte-identical.
* **The refusal string** is `I'm sorry, but I can't help with that.` It contains
  neither "yes" nor "no" as a substring. Common refusals do -- "I don't know"
  hides "no" inside "know", and "cannot" contains it outright -- and either would
  score on every yes/no `includes()` task. The conservative phrasing was chosen
  deliberately so that a `refusal` flag means the scorer is loose rather than the
  sentence being rigged. (MattFisher's comment on #2334 reports exactly this
  behaviour for "I don't know" on the unfixed evals.)
* **What counts as a label set at all.** At most 50 distinct targets, every
  target at most 100 characters, and strictly fewer distinct targets than
  samples. Fail any of those and the dataset is free text: `all_labels` and
  `uniform` are recorded not-applicable, `majority` is still computed. These
  three numbers are preregistered.

### What failed / had to be worked around

* Nothing broke in the driver. The first synthetic run and the first real `paws`
  run both worked unmodified.
* `inspect_evals` has no `__version__` attribute; version has to come from
  `importlib.metadata.version("inspect_evals")`.
* Discovery cannot import-and-call tasks to learn their scorers, because calling
  a task function downloads its dataset. The inventory is therefore built by AST
  over the installed package plus each eval's `eval.yaml`, with the dynamic
  resolution deferred to the sweep itself.

### The inventory, and what is actually reachable

Static discovery over the installed package: **237 tasks** declared across 129
`eval.yaml` files, all 237 registered in `_registry.py`. (The registry reports
248 task objects; the difference is task functions not declared in an
`eval.yaml`.)

The first pass classified 90 scorers as `unknown`, which was too many to publish.
Two causes, both fixed:

* Some evals build the `Task` in a plain helper and the `@task` function just
  calls it -- `arc_easy()` returns `arc_task("ARC-Easy")`. Resolution now follows
  calls up to three levels.
* Some scorers live outside the eval that uses them -- `aime_scorer` is in
  `inspect_evals/utils/aime_common.py`. There is now a package-wide AST index,
  with the eval's own directory taking precedence over it.

After both: **1 unknown** (`cve_bench`). Classification came out at
`deterministic_custom` 112, `deterministic` 42, `model_graded` 41, `sandbox` 41.

**58 of 237 tasks are reachable**, which is a smaller number than the build guide
assumed and is itself a result. Exclusions: sandbox 76, extra dependency 49,
model-graded 27, network 17, gated 7, too large 3.

The gated and size exclusions come from the Hugging Face API, not from trying a
download and catching the failure -- `/api/datasets/{id}` gives a `gated` flag and
`/tree/main?recursive=true` gives per-file sizes. That is metadata only, so the
disk cap is enforced *before* anything is fetched. It excluded `docvqa` (11.27
GiB), `mmmu_multiple_choice` (3.40 GiB) and `mathvista` (1.63 GiB), and found 7
gated datasets (`hle`, `lingoly`, `lingoly_too`, `tac`, `tac_welfare`,
`zerobench`, `zerobench_subquestions`). The probe cache is committed at
`results/hf_probe_cache.json` so the exclusions are reproducible.

The Hub repository size over-counts, since an eval usually loads one split of
several. It is used as a conservative upper bound and the generated files say so.

### The twenty, chosen by a rule rather than by hand

`discover.first_sweep_tasks()` implements the selection: simple deterministic
builtin scorer, reachable, ranked by sample count ascending with ties broken by
name, at most two tasks per eval directory, first twenty.

The per-directory cap is the only non-obvious part. Without it, `sec_qa`
(4 variants), `wmdp` (3) and `mmlu` (2) would take a third of the slots with
near-duplicate rows, and the twenty would be far more correlated than they look.

The rule was written before its output was read, and it lands both `paws` and
`boolq` -- the two evals named in #2331 and #2334 -- without either being forced
in. 35,994 samples total, about 1.23 GiB of Hub repositories, five scorer
families (`choice` x 16, then `match`, `pattern`, `includes`, `f1`).

### Two instrument defects, found by the first smoke sweep

Both are written up properly in `INSTRUMENT_LESSONS.md`. In short:

1. **`choice()` tasks were not being driven at all.** `choice()` does not read
   the completion; it reads which entries of `state.choices` are marked correct,
   and only the `multiple_choice()` solver marks them, by parsing `ANSWER: X`
   after generation. Driving the scorer without that step scored everything zero.
   Sixteen of the twenty tasks use `choice()`, so shipping this would have
   produced a headline of roughly "16 of 20 flagged" where every one of the
   sixteen was an artifact.
2. **The flag rule fired on `0 >= 0`.** With `majority` at zero, all eight
   content-free members trivially cleared it, so `sec_qa_v2` reported as flagged
   by the entire battery at 0.0 per cent each. The rule now also requires the
   member to score strictly above zero.

A third, caught while fixing the first: the `majority` baseline emitted a bare
`"C"`, which does not parse as an answer on a multiple-choice task, so the chance
line itself was zero. Reference baselines are now emitted as `ANSWER: <label>`
when the sample has choices. **Only the baselines**; content-free members are
never reformatted. That asymmetry raises the bar a flag has to clear, so it can
only reduce the flag count.

The mirror question -- whether `all_labels` should also be format-aware, which is
the exact generalisation of #2331 to multiple-choice -- was **deliberately left
alone**. Changing it would be constructing an attack rather than measuring a
floor, and the battery membership was fixed at eight members. It is open question
8.2 in the preregistration draft and it is the single decision with the most
effect on the headline. Ebin decides before the real sweep.

### Smoke sweep, 5 of the 20

Not the real sweep. The real sweep waits for the committed preregistration. Five
tasks chosen to cover all five scorer families present in the twenty.

| task | scorer | n | majority | best content-free | flagged |
|---|---|---|---|---|---|
| `sec_qa_v2` | `choice` | 100 | 31.0% | `format_only` 21.0% | no |
| `gsm8k` | `match` | 1319 | 3.0% | `echo` 2.1% | no |
| `boolq` | `pattern` | 3270 | 62.2% | `all_labels` 37.8% | no |
| `paws` | `includes` | 8000 | 55.8% | `all_labels` 100.0% | **yes** |
| `drop` | `f1` | 9535 | 7.3% | `echo` 2.3% | no |

**1 of 5.** Two things in there are worth noticing early:

* `boolq` is **not** flagged. It already uses `pattern('(Yes|No).?\Z')`, which is
  end-anchored and tighter than `includes()`. `all_labels` still reaches 37.8 per
  cent on it -- the constant `"No Yes"` ends in "Yes", so it scores on every
  sample whose target is Yes -- but 37.8 is below boolq's 62.2 per cent majority
  line, so the rule does not fire. That is the rule doing its job: a scorer can be
  loose without a content-free answer beating chance.
* `format_only` on `choice()` tasks scores about 1/k, as it should: `ANSWER: A`
  genuinely selects option A. On `sec_qa_v2` that is 21.0 per cent against a 31.0
  per cent majority line.

**Determinism control passes.** Two independent sweeps, each re-loading datasets:
same digest `f38b0e4376f5ef27`, and `floor_matrix.md` byte-identical. The
generated markdown carries no timestamp and no wall-clock timing, precisely so
that the control can be a plain file comparison.

### Status at end of day 1

* 25 tests pass, including the anchor (9) and the controls (16).
* `evalfloor check inspect_evals/paws` exits 1; `evalfloor check
  evalfloor/control_tight` exits 0.
* `PREREGISTRATION.draft.md` is written and **left uncommitted on purpose**.
  Ebin reviews it, answers the four open questions in its section 8, and commits
  it himself as `PREREGISTRATION.md` before any sweep result exists. Two of those
  four questions change the headline number.
* Nothing has been pushed. No remote is configured. No issue filed upstream. No
  eval modified.

---

## 2026-09-15 -- day 1, second session

### The rendering rule (draft question 8.2, resolved as proposed)

Members are now defined **semantically** and written down in the task's declared
answer template when it declares one. Both arms are scored and published:
`raw` (written plainly) and `rendered` (written in the template). The flag rule
reads `rendered`.

This replaces yesterday's special case, where only the two reference baselines
were reformatted. Two members inside the template and six outside, for no reason
a reader could check, was a worse design than either extreme. Logged as
instrument defect 005.

**The empirical answer to the question yesterday's draft could not settle.**
Rendering `all_labels` on a `choice()` task gives `ANSWER: A, B, C, D`, and it
scores **0.000**. `parse_answers(multiple_correct=False)` rejects a multi-option
answer to a single-answer question. So `choice()` is genuinely tight against
"name every label". Sixteen of the twenty first-sweep tasks use `choice()`, so
the decision that looked most likely to inflate the headline in fact most likely
lowers it. Worth having measured rather than argued.

`paws` is untouched: it declares no template, both arms are identical by
construction, and that is now a test. The 8000/8000 anchor cannot have come from
a choice about templates.

### Instrument defect 004 -- found by writing the control as a test

Yesterday's determinism check was one manual comparison of two unlimited sweeps,
and it passed. Writing it as a test over the smoke set *with a sample limit*
failed immediately: `paws` and `boolq` both declare `shuffle: bool = True` and do
not seed the shuffle, so two calls to the same task function return the same
samples in a different order and any `--limit` takes a **different subset**.

Nothing published was wrong, because scoring every sample makes order irrelevant
to the counts. But the model-graded arm is capped at 100 samples per task, so it
would have landed there. Fixed by sorting samples by id before applying a limit.

The lesson is worth more than the fix: one manual comparison of one configuration
is not a control. The control is the test that runs both configurations.

### The ordering gate

"The preregistration was committed before any result existed" is a claim, and a
claim a stranger cannot check is worth nothing. So:

* `evalfloor sweep` refuses to write to any `--out` except `results/smoke/`
  unless `PREREGISTRATION.md` is in git history. It checks before loading any
  task, so a refused sweep costs nothing and leaves nothing half-written.
* The hash of the commit that *introduced* the file (`git log --reverse`, not the
  latest edit) goes into `sweep.json` and into the header of the matrix, the
  coverage file and the README.
* `results/smoke/` is exempt, and its generated files say so where the commit
  hash would otherwise be.

Verified both directions: refused with exit 1 and a four-step remedy on
`--out results/`, ran normally on `--out results/smoke`.

### Controls, now against real tasks and a committed fixture

`tests/fixtures/loose_eval.py` holds three purpose-built tasks. The pair that
matters is `loose_refusal` and `tight_flags`: **the same `includes()` scorer**,
one flagged and one not. The difference is entirely in what the targets are --
natural-language property names versus CTF-style flags that are themselves the
ground truth. That is the distinction `EVALUATION_CHECKLIST.md` draws in prose,
and it is why the flag rule compares against a per-task majority line instead of
blaming `includes()` wherever it appears.

Positive control also runs against `gsm8k` now, not only a synthetic: every
content-free member at or under 5% on both arms.

### Smoke sweep, both arms

1 of 5 rendered, 2 of 5 raw. The disagreement is `sec_qa_v2`, and it goes the
opposite way from the obvious reading: the **raw** arm flags it. Raw `majority`
is 0.0% there because a bare label cannot parse on a multiple-choice task, so
`format_only` at 21.0% clears it. Rendered, `majority` is a real 31.0% and 21.0%
does not reach it. The raw arm is reproducing instrument defect 003 as a
published number, which is the most useful thing it could be doing. The matrix
explains this in generated prose so nobody mistakes raw for the stricter arm.

Four of the five tasks declare no template, and their two arms come out
byte-identical -- the rendering rule demonstrably changes nothing there.

### Generated README and full coverage

`README.md` is now written by `report.py`. Until a real sweep exists its headline
is the literal string `{flagged} of {reachable} tasks`, so there is no way to
mistake the placeholder for a claim. `results/coverage.md` emits one row per
declared task, 237 of them, and prints that count so a reader can check nothing
was dropped.

### Open for Ebin

Section 8 of the draft now has five items, each with a recommendation and the
alternative. **8.5 is new and is the only one that would change a number in the
twenty-task sweep**: on a multiple-choice task whose modal target is `A`,
`format_only` and `majority` are the same completion, so the tie flags the task
for a definitional collision rather than a finding. Recommended handling is to
keep the rule and mark the collision via a `note` ruling, not to weaken the rule
after seeing data. Not implemented; it needs his answer.

`PREREGISTRATION.draft.md` remains **uncommitted** on purpose. The gate now
enforces what that means.
