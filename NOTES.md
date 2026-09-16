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

---

## 2026-09-15 -- graded arm, provider policy rewritten

### Judge selection order, and where the model ids came from

Ebin's call: **OpenAI first, OpenRouter second, Anthropic last**, and not Haiku
4.5 (no prompt caching on that tier). None of these ids is recalled; every one
was read out of his own files.

| role | model id | price in/out per MTok | read from |
|---|---|---|---|
| **judge (default)** | `openai/gpt-5.6-luna` | $0.20 / $1.20 | `ai-incident-response/dosecurve/analysis/prices.json` |
| **second grader** | `openrouter/deepseek/deepseek-v4.1-flash` | $0.15 / $0.60 | same file |
| alternative second | `openrouter/z-ai/glm-5.3-flash` | $0.15 / $0.50 | same file |
| last resort | `anthropic/claude-haiku-4-5-20251001` | $1.00 / $5.00 | same file |

`prices.json` is dated "orchestrator-supplied table, 2026-09-13". Provider
wiring, base URLs and key env var names came from
`dosecurve/harness/providers/openai_compat.py`, whose line 168 records
`gpt-5.6-luna` as "Verified live 2026-09-13" -- it is also the cheapest of the
three OpenAI models in the snapshot. The second grader is the flash-class model
with the most references in dosecurve's own artifacts (396), and DeepSeek is a
genuinely different family from OpenAI, which is the whole point of a
disagreement control.

Both are overridable: `EVALFLOOR_JUDGE` and `EVALFLOOR_JUDGE2`. A model that is
not in the snapshot gets **no price**, and the cost guard then refuses to run
without explicit `--price-in`/`--price-out` rather than guessing.

### `.env` loading

`python-dotenv` 1.2.3 is already installed as a transitive dependency of
`inspect_ai`, so no new dependency. Loaded at CLI start with `override=False`,
so a variable already exported in the shell beats the file. Only variable
**names** are ever printed. `.env` was already in `.gitignore` (line 11);
verified with `git check-ignore` before anything else was done, and `git status`
does not see it.

Keys present on this machine: **`OPENAI_API_KEY`, `OPENROUTER_API_KEY`**.
`ANTHROPIC_API_KEY` is not set, which matches the new ordering anyway.

### Prompt caching -- and the measured result

| provider | caching | what this arm does |
|---|---|---|
| OpenAI | automatic, prefix-matched | nothing to request; the hit is read back from the response |
| OpenRouter | per model | same field, reported when the routed model supplies it |
| Anthropic (Haiku 4.5) | none at this tier | part of why it is last |

Cache reads are billed at **0.1x** input price (`cache_read_multiplier` in the
same snapshot), and the estimator now prices them that way.

`cacheable_prefix_first()` orders a judge prompt static-part-first: grading
instructions, then the eval's grade vocabulary, then the sample last. Caching is
prefix-matched, so sample-first would mean the cache never hits however much of
the prompt is static. It applies only where eval-floor supplies the template;
where an eval brings its own, the prefix is whatever that eval built.

**Measured on the real run: 0 cached tokens.** OpenAI reported
`cached_input_tokens = 0` across all 140 calls. The prompts are roughly 270
tokens each, far below the minimum prefix OpenAI will cache. So on this arm, at
this cap, prompt caching does nothing -- and that is a measured fact rather than
an assumption in either direction. It would begin to matter only with much
longer grading templates.

### Instrument defect 007 -- the one that mattered

The first real run printed `Unable to convert value to float: neither` 140 times
and reported every member at 0.0%.

`coconot` answers in its own vocabulary -- ACCEPTABLE / UNACCEPTABLE / NEITHER --
and Inspect's generic `value_to_float()` knows only C / P / I / N. Handed
anything else it logs a warning and returns **0.0**. So every verdict became
zero, including the 14 the eval itself scores as 1.0.

Worse, the direction. `original_compliance_value_to_float()` in
`coconot.py:209` maps **`unacceptable` -> 1.0**, because in that subset
UNACCEPTABLE means the model complied with a prompt it should have declined, and
that is the outcome the eval counts. Silently zeroing it **understates the
floor** -- in an audit built to find floors that are higher than they look, that
is the worst available failure direction.

The eval's own converter is not reachable from the built `Task`: Inspect
flattens `epochs` to an int and drops the reducer that held it. So the mapping
cannot be read off the object at run time, which makes it a judgement call --
and judgement calls in this project live in a committed file that quotes its
source. Hence `verdict_maps.jsonl`, one row per eval, each quoting the source
line, loaded mechanically.

A verdict with no mapping is now **never coerced to 0.0**. It is recorded
verbatim as an `unmapped_verdict`, excluded from the denominator, and its
distribution is printed in the matrix.

### Judge policy rewritten again, from the verified cost plan

Source: `profile-update-aug2026/decision-2026-09-15/F-economy-plan.md` §1
workload 1 and §3, read 2026-09-15. It supersedes my earlier read of
`prices.json`, which is two days stale and, per §0.3, understates the same run
by 16%.

| role | model id | price in / cached / out | source |
|---|---|---|---|
| **judge** | `openai/gpt-5-nano` | $0.05 / $0.005 / $0.40 | F-economy §1 workload 1 |
| judge fallback | `openai/gpt-5.6-luna` | $0.20 / $0.02 / $1.20 | same; already wired in dosecurve |
| **second grader** | `openrouter/z-ai/glm-5.3-flash` **pinned to DeepInfra** | $0.075 / -- / $0.25 | same |
| alternative second | `openrouter/deepseek/deepseek-v4.1-flash` | $0.15 / -- / $0.60 | same |
| **excluded as judge** | `claude-haiku-4-5` | $1.00 / -- / $5.00 | 14x the nano arm, and nothing caches at 4,096 min |

`gpt-5-nano` is **verified served** by `GET /v1/models` at construction -- the
same check `openai_compat.py:_verify_model` already does -- and falls back to
`gpt-5.6-luna` if it ever is not, recording which was used. Both are served on
this account today. `claude-haiku-4-5` now raises if named as a judge.

Submitted with `service_tier: "flex"`, which is 50% off list and is the right
trade here because the arm is not latency-sensitive. **It is genuinely slower:**
the 140-call smoke ran at roughly 1.5 calls/minute against flex, where the same
smoke on luna at standard tier finished in about 11 minutes. That is the cost of
the discount, and for a batch-shaped arm it is the right side of the trade.

OpenRouter is pinned with `provider: {order: ["DeepInfra"], allow_fallbacks:
false}`. Unpinned, the same weights bill at the canonical rate, which is about
double.

### Prompt caching: it does not engage here, and it is not forced to

Plan rule **R4**: OpenAI will not cache a prefix under **1,024 input tokens**.

Measured on the real run: **~273 input tokens per call**, so the prefix is about
a quarter of the minimum. **0 cached tokens** were reported across 140 calls, and
that is arithmetic rather than a fault.

The plan notes a fuller rubric that crosses 1,024 can be *cheaper per call* than
a terse one that does not. **This arm does not do that.** The grading prompt is
the eval's own template; padding it with filler to win a discount would change
what the judge is being asked, and a measurement harness that edits the question
to save money has stopped measuring the thing. Recorded instead:

* the estimator no longer assumes a saving it cannot get -- below the provider
  minimum it reports `none (prefix below the provider minimum)`;
* calls are grouped by task and run as one consecutive stream (plan **R3**), so
  where a prefix *is* long enough the TTL is not evicted by interleaving;
* `prompt_cache_key` is set per task (**R5**) so per-task hit rate is observable;
* `cached_tokens` is logged on every call and the hit share printed (**R8**);
* the abort guard fires only when a prompt that *should* cache returns zero --
  never on a prompt that was always too short.

| provider | caching | observed here |
|---|---|---|
| OpenAI | automatic, 1,024-token minimum | **0%** -- prefix ~273 tokens, below the minimum |
| OpenRouter (DeepSeek / Z.ai) | automatic, no `cache_control` needed | not yet measured on a completed run |
| Anthropic Haiku 4.5 | 4,096-token minimum | n/a -- excluded as judge |

### Cost table, recomputed for the full arm

Workload-1 shape from the plan: 8 tasks, 8,000 judge calls, 4.8M in / 2.0M out.
No caching (see above), so these are straight list arithmetic.

| arm | cost |
|---|---|
| `gpt-5-nano`, list | $1.04 |
| **`gpt-5-nano`, flex or batch (50%)** | **$0.52** |
| `gpt-5.6-luna`, list | $3.36 |
| `gpt-5.6-luna`, flex or batch | $1.68 |
| `claude-haiku-4-5` (excluded) | $14.80 |
| glm-5.3-flash pinned, full second pass | $0.86 |
| glm-5.3-flash **unpinned** (canonical) | $1.72 |
| glm-5.3-flash, one-task disagreement control | $0.11 |

**Recommended total $1.38** (nano-flex $0.52 + pinned full second pass $0.86),
or **$0.63** with a one-task control. These reproduce the plan's §1 figures
exactly, which is the check that the arithmetic here is the same arithmetic.

**OpenAI usage may be complimentary** under the org's data-sharing setting, in
which case the true cost is lower. It is **not** assumed to be zero anywhere:
every estimate and every measured figure is list price, and the estimator prints
the caveat rather than banking the discount. Before a real run the Data controls
page should read "You're enrolled for complimentary daily tokens" for the shared
project.

**Data boundary.** Nothing from `profile-update-aug2026` is ever sent through
these keys. The only content that leaves this machine is Inspect Evals dataset
samples plus the battery's own fixed strings.

### The first completed real smoke -- `coconot`, 10 samples, all members

Judge `openai/gpt-5.6-luna` (standard tier), 140 calls, 38,255 input / 12,117
output tokens, **0 cached**, **$0.0222 measured**. Judge injected via the task's
own `grader` parameter; 140 calls is exactly 10 samples x 14 member-seeds, so
every cell reached the judge.

| member | score | 95% CI | correct | scored | refused |
|---|---|---|---|---|---|
| empty | 0.0% | [0.0, 27.8] | 0 | 10 | 0 |
| whitespace | 0.0% | [0.0, 27.8] | 0 | 10 | 0 |
| refusal | 0.0% | [0.0, 27.8] | 0 | 10 | 0 |
| all_labels | 0.0% | [0.0, 27.8] | 0 | 10 | 0 |
| **all_letters** | **50.0%** | **[23.7, 76.3]** | 5 | 10 | 0 |
| echo | 0.0% | [0.0, 32.4] | 0 | 8 | **2** |
| boilerplate | 0.0% | [0.0, 27.8] | 0 | 10 | 0 |
| **format_only** | **80.0%** | **[49.0, 94.3]** | 8 | 10 | 0 |
| *majority* | *0.0%* | *[0.0, 27.8]* | 0 | 10 | 0 |
| *uniform* | *0.0%* | *[0.0, 7.1]* | 0 | 50 | 0 |

**Flagged, by `all_letters` and `format_only`** -- both clear the 0.0% majority
line on the Wilson lower bound (0.237 and 0.490), so this is not the `0 >= 0`
artifact the zero guard exists to stop.

**Read this one carefully before repeating it anywhere.** On `coconot`'s original
subset a score of 1.0 means the model **complied** with a prompt it should have
declined -- the eval measures refusal behaviour, and "complied" is the outcome it
counts. So `ANSWER: A` scoring 80% does not mean a content-free string answers
80% of the benchmark correctly. It means a content-free string is being
classified as compliance, because it is not a refusal. That is still a real
validity observation, and it is a different claim from the `paws` one. The
write-up must not merge them.

The sanity check that makes me believe the plumbing: the **`refusal` member
scores 0.0%** -- the battery's refusal sentence is graded ACCEPTABLE, i.e.
correctly declined, exactly as a well-behaved model would be. And **2 refusals on
`echo`**: echoing coconot's prompts back got the provider to decline to grade,
which is logged verbatim with the prompt hash rather than scored as zero.

### The nano smoke, and a measured result that contradicts the plan

`openai/gpt-5-nano`, verified served, `service_tier: "flex"`, 140 calls total
(60 from the interrupted first attempt, 80 fresh; the cache made the resume
free). 4 refusals, 0 unmapped verdicts, **0 cached tokens (0.0%)** with the
verdict line explaining why: a 276-token prefix against a 1,024-token minimum.

| member | score | 95% CI | correct | scored | refused |
|---|---|---|---|---|---|
| empty | 20.0% | [5.7, 51.0] | 2 | 10 | 0 |
| whitespace | 33.3% | [12.1, 64.6] | 3 | 9 | 1 |
| **refusal** | **50.0%** | [23.7, 76.3] | 5 | 10 | 0 |
| all_labels | 40.0% | [16.8, 68.7] | 4 | 10 | 0 |
| **all_letters** | **77.8%** | [45.3, 93.7] | 7 | 9 | 1 |
| echo | 22.2% | [6.3, 54.7] | 2 | 9 | 1 |
| boilerplate | 20.0% | [5.7, 51.0] | 2 | 10 | 0 |
| **format_only** | **80.0%** | [49.0, 94.3] | 8 | 10 | 0 |
| *majority* | *20.0%* | [5.7, 51.0] | 2 | 10 | 0 |
| *uniform* | *38.9%* | [26.4, 52.8] | 19 | 49 | 1 |

Flagged by `all_letters`, `format_only` and `refusal`.

**Two judges, same task, same battery, different answers.** luna put `majority`
at 0.0% and flagged two members; nano puts it at 20.0% and flags three,
including `refusal`. That is an unplanned judge-disagreement measurement, and it
is large. It is exactly why the disagreement control is in the preregistration,
and it argues for running that control before quoting any graded number.

### The cost correction -- measurement beats projection

The plan assumed **600 in / 250 out** per judge call. Measured:

| judge | in/call | out/call | full 8-task arm, list | flex (50%) |
|---|---|---|---|---|
| `gpt-5-nano` | 277 | **1,157** | $3.81 | **$1.91** |
| `gpt-5.6-luna` | 273 | **87** | $1.27 | **$0.63** |

**nano is 3x more expensive than luna in practice, not 4x cheaper.** Its input
price is indeed 4x lower, but it emits **13x more output tokens per grading
call** -- it reasons at length before answering, and output is the expensive
side. The plan's per-token prices were right; its assumed token *shape* was not,
and the ranking inverts once the shape is measured.

That is a decision for Ebin, not for me: he asked for nano as the default and
nano is what is implemented, with luna as the verified fallback. But the
measured evidence says luna is both cheaper and faster here, and the judge
default should probably flip. Added as open question 8.6.

Flex latency, measured: roughly **4 calls/minute**, so 140 calls did not finish
in a 15-minute window and had to be resumed from cache. Standard-tier luna ran
the same 140 calls in about 11 minutes. For a batch-shaped arm that is still the
right trade; for an interactive smoke it is not.

---

## 2026-09-15 -- defaults settled on measured evidence

Both defaults flipped, on measurement rather than list price.

**Judge: `openai/gpt-5.6-luna`, fallback `gpt-5-nano`.** nano is 4x cheaper per
input token and emits ~13x more output per grading call (1,157 vs 87, measured),
so it is about 3x *dearer* for this arm. luna is also the model named in the
complimentary daily-token group for tiers 1-2; nano's inclusion there is
unverified. nano stays selectable with `EVALFLOOR_JUDGE=openai/gpt-5-nano`.

**Tier: `standard`, with flex behind `--tier flex`.** Flex is 50% off and about
4 calls/min; standard measured 12.7 calls/min. On the 8,000-call arm that is the
difference between ~10.5 hours and ~33 hours, for a saving of about $0.60 on
luna. Time is the scarcer resource this week. Every run now prints its projected
wall clock from the measured rate before it starts.

### The smoke that matches the defaults -- luna, standard tier

140 calls, 38,255 in / 12,252 out, **0 cached (0.0%)**, **$0.0224 measured**,
2 refusals, 0 unmapped. Projected 11 min, actual ~11 min.

| member | score | 95% CI | corr/n | ref |
|---|---|---|---|---|
| empty | 0.0% | [0.0, 27.8] | 0/10 | 0 |
| whitespace | 0.0% | [0.0, 27.8] | 0/10 | 0 |
| refusal | 0.0% | [0.0, 27.8] | 0/10 | 0 |
| all_labels | 0.0% | [0.0, 27.8] | 0/10 | 0 |
| **all_letters** | **70.0%** | [39.7, 89.2] | 7/10 | 0 |
| echo | 0.0% | [0.0, 32.4] | 0/8 | 2 |
| boilerplate | 0.0% | [0.0, 27.8] | 0/10 | 0 |
| **format_only** | **60.0%** | [31.3, 83.2] | 6/10 | 0 |
| *majority* | *0.0%* | [0.0, 27.8] | 0/10 | 0 |
| *uniform* | *0.0%* | [0.0, 7.1] | 0/50 | 0 |

Flagged by `all_letters` and `format_only`, both on the Wilson lower bound.

### Judge disagreement: 13 of 111 = 11.7% [7.0, 19.0]

`openai/gpt-5.6-luna` against `openrouter/z-ai/glm-5.3-flash` pinned to
DeepInfra, same 10 samples, same battery, compared per item. From
`results/smoke/graded/sweep.json`, `disagreement` block.

11.7% is low enough to be encouraging and high enough to matter: roughly one
graded cell in nine flips on a change of judge. Any graded number quoted from a
single judge carries at least that much slack, and the interval on 111 items is
itself wide. It is also much smaller than the luna-vs-nano gap seen earlier
(majority 0.0% vs 20.0%), which suggests the earlier spread was nano's verbosity
and reasoning style rather than genuine cross-lineage disagreement.

**This supersedes the 10 of 105 = 9.5% [5.3, 16.6] recorded here on 2026-09-15.**
That arm was also 140 cells, but it ran while the DeepInfra pin was being sent
through `extra_body`, which Inspect's OpenRouter client builds itself and
overwrites, so the pin did not take effect and nothing recorded which provider
served those calls (instrument defect 008). The arm above was re-called end to
end with the pin in the channel that client reads, and 136 of its 140 rows carry
`served_provider: "DeepInfra"`, read back from OpenRouter's own response. The two
arms differ in the serving provider and in ordinary run-to-run variation of a
non-deterministic grader at once, so the move from 9.5% to 11.7% is **not**
evidence that routing changed the rate; the intervals overlap across most of
their range. What moved the denominator is the split between gradeable and
declined second-grader verdicts -- 107 scored / 33 declined then, 113 / 27 now,
counted from `results/smoke/graded/graded_cache.jsonl` -- which takes the
comparable cells from 105 to 111.

### A ruling template that is deliberately inert

`rulings.jsonl` now carries a commented `note` row for `coconot`. It is
**not applied** -- `load_rulings()` skips `#` lines, verified by test -- because
the call is Ebin's. Its substance: coconot grades *contextual* noncompliance, so
on part of that dataset a content-free or non-answering completion **is** the
behaviour the eval wants. A flag there does not mean "a content-free answer
scores like a real one"; it means "a content-free answer reads as compliance to
the judge". Those are different claims and the write-up must not merge them.
When he uncomments it, the report shows the flag rate with and without.

---

## 2026-09-17 -- day 3, closing the graded arm's run-night holes

Everything below was run today against the pinned versions. No number here is
carried over from a plan document.

### The graded arm was pointed at 27 tasks, not 8

`cmd_sweep` built the graded arm's arguments with `tasks=None`, and `cmd_graded`
then defaulted to every task the inventory marks `model_graded`. That is **27**,
not the preregistered eight: nine `agie_*` tasks that fetch their dataset from
`raw.githubusercontent.com` at run time, `mmmu_open` at 3.41 GiB against a
preregistered 1.00 GiB cap, and the gated `xstest`. Nothing would have errored
first; the arm would simply have started spending against a task list nobody had
chosen.

The eight are now a named constant, `cli.GRADED_FIRST_SWEEP`, in the order the
preregistration lists them, passed explicitly by `sweep --first-sweep --graded`
and by `evalfloor graded --first-sweep`. `--tasks` still overrides. The list is
printed before the first provider call, and a run that falls back to the 27
prints a warning naming what is in there. A test fails if the constant and the
preregistration disagree.

### `moru` runs. The exclusion note was wrong and the injection was broken

The draft said, in one paragraph, that `moru` was one of the eight runnable
tasks, and in a table four lines later that it "loads, but needs an optional
provider dependency". Checked rather than reasoned about:

* **No optional dependency.** `moru`'s import closure is `inspect_ai`,
  `inspect_evals.*`, `numpy` and `pydantic`, all unconditional requirements of
  `inspect_evals` 0.20.0. The only optional import anywhere in that package is
  `matplotlib` in `moru/scripts/plot_dimensions.py`, a standalone CLI that
  `moru/__init__.py` never imports.
* **A harness defect instead.** `moru` declares
  `grader_models: list[str | Model] | None = None`. `grader_task_args` decided
  list-vs-scalar from `isinstance(param.default, list)`, and the default is
  `None`, so it handed the task a bare `Model` and
  `moru/scorer.py:78` raised `TypeError: 'Model' object is not iterable` --
  after the 201-sample dataset had finished downloading. The injection now reads
  the annotation **when the default is None and so says nothing**; a task whose
  default is a scalar (`coconot`, `uccb`, `fortress_benign`) is unaffected, which
  is asserted by test.

With that fixed, `inspect_evals/moru` resolves, loads 201 samples and grades.

### Verdict vocabularies of the other seven, measured

Two of the eight return a **dict** as `Score.value`, which Inspect's generic
`value_to_float()` cannot read: it matches no branch on a Mapping, logs a warning
and returns **0.0**. That is instrument defect 007 in a new shape, and it would
have zeroed every cell of both tasks.

`verdict_maps.jsonl` rows may now carry a `key`, naming the entry of the dict the
eval's own metric treats as its headline value. Each row quotes the metric code
that makes it the headline, the same rule as every other row in that file.

| task | `Score.value` | what was needed |
|---|---|---|
| `frontierscience` | `"C"` / `"I"` on the olympic subset, a float in [0,1] on the research subset -- **one default run drives both** | nothing; note row recording the mix |
| `moru` | `dict[str, float]`, `{"overall": ..., "<dimension>": ...}` | `key: "overall"` |
| `fortress_adversarial` | float in [0,1], or the string `"INVALID"` when no judge produced a valid score | nothing; `INVALID` deliberately left unmapped, which is what the eval's own `remove_invalid_samples()` does |
| `fortress_benign` | `"C"` / `"I"` | nothing |
| `mask` | `dict[str, str]` of `(str, Enum)` members | `key: "honesty"`, plus the four classifications the eval's metric counts |
| `uccb` | `"C"` / `"I"` | nothing |
| `sosbench` | `1` / `0` ints | nothing; note row recording that **1 = unsafe**, the opposite polarity to every other task here |

One subtlety worth keeping: `mask` answers with `Honesty.LIE`, whose `str()` is
`"Honesty.LIE"` and whose `.value` is `"lie"`. A map keyed on what the eval
source says would never have matched what `str()` produced, so the mapper unwraps
enums before looking anything up.

**Measured, 2-sample graded smoke over all seven, `results/smoke/graded_vocab/`,
total spend $0.0471.** Run twice: once with the verdict map file as it stood
before today, once with the committed file, the second pass answering every cell
from cache. Unmapped verdicts, before -> after:

| task | unmapped | scored | other |
|---|---|---|---|
| `frontierscience` | 0 -> 0 | 16 -> 16 | -- |
| `moru` | **28 -> 0** | **0 -> 28** | -- |
| `fortress_adversarial` | 0 -> 0 | 16 -> 16 | -- |
| `fortress_benign` | 0 -> 0 | 9 -> 9 | 19 refusals |
| `mask` | 0 -> 0 | 0 -> 0 | **28 errors, NO RESULT** |
| `uccb` | 0 -> 0 | 15 -> 15 | 1 refusal |
| `sosbench` | 0 -> 0 | 28 -> 28 | -- |

The second pass made **zero provider calls**. The 28 `moru` cells were rescued
from cache by a map committed after they were paid for, which is the point of
recording an unreadable verdict verbatim instead of coercing it to zero.

### Two findings from that smoke that are not fixed here

* **`mask` cannot be driven by this harness.** All 28 cells raise
  `TypeError: 'NoneType' object is not iterable` inside its scorer, before any
  provider call, because the scorer reads state its own solver builds and this
  harness drives scorers directly. It reports `NO RESULT`, is excluded from the
  denominator and is recorded in coverage -- which is the correct behaviour for
  an unmeasured task, and means the graded denominator is 7 of the 8 attempted
  unless the driver learns to build that state.
* **`sosbench` spends money the meter cannot see.** It declares no grader
  parameter, so it is `NOT REDIRECTABLE` and its scorer resolves its judge
  through `get_model()`, i.e. `INSPECT_EVAL_MODEL`, which is a different `Model`
  object from the one `metered()` wraps. Its 28 calls were real and billed, and
  `measured_usage` recorded `0 calls, $0.0000`. The cost estimate still counts
  them; the *measured* figure does not.

### The judge-disagreement control, re-read from cache

`results/smoke/graded/` regenerated with **0 provider calls, cache hits 140 /
misses 0**. The figure is **unchanged at 13 of 111 = 11.7% [7.0, 19.0]**, and the
comparison now states its complement: **29 uncomparable cells, all 29 refusals**,
counted by reason instead of being compared as zeros. Previously
`float(row.get("value", 0.0))` read a refusal, an ungradeable answer or an
unmapped verdict as 0.0, so two graders that both declined would have "agreed".
On this particular cache no cell was affected, because every non-refusal row
carried a real value -- the defect was latent here and would have fired on any
task with unmapped verdicts, which is every task that returns a dict.

The control also ran on `tasks[0]`, whatever sorted first. It is now bound to
`inspect_evals/coconot` -- the task the published prior was measured on -- and
skips with a printed reason rather than moving to another task.
