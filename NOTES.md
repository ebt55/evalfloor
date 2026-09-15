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
