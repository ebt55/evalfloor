# Preregistration -- eval-floor week 1

> **DRAFT. NOT COMMITTED.** Written by an agent on 2026-09-15 from the build
> guide and from what the harness actually did on the day. Ebin reviews it,
> changes what he disagrees with, and commits it himself as `PREREGISTRATION.md`.
>
> Every item in section 8 was **decided on 2026-09-17, before the sweep ran**.
> Each records the alternative it was chosen over.
>
> Accuracy edits made at that review, none of them a decision: section 7's
> defect count corrected from five to eight; the description of the `coconot`
> ruling's inertness corrected to what the code actually guarantees (comment
> lines are skipped by `load_rulings()`; no test pins it); and the ruling row
> itself was uncommented on 2026-09-17, before any result existed.
>
> The point of this file is its git timestamp, and that is now enforced in code
> rather than in good intentions: `evalfloor sweep` refuses to write to any
> output directory except `results/smoke/` unless `PREREGISTRATION.md` is already
> in git history, and it stamps the hash of the commit that introduced it into
> `sweep.json` and into the header of every generated file. A stranger can check
> the ordering with `git log -- PREREGISTRATION.md`.

---

## 1. The negative-result threshold, stated first

**If fewer than five reachable tasks are flagged, the finding is that the
Inspect Evals collection is tighter than the single known case suggested, and
the write-up says so in its first paragraph.**

That sentence is at the top, before the method, because it is the claim this
project is most likely to have to make and the one it would be most tempting to
bury. The five-task threshold is fixed now and does not move after the numbers
are in.

Two related honesty rules:

* The flag rate is reported **both before and after** `rulings.jsonl` is applied,
  so a reader can see how much of the headline is a judgement call.
* The flag rate is reported on **both arms** of the battery (section 3), so a
  reader can see how much of the headline depends on the rendering rule.

---

## 2. The question

For each task in the Inspect Evals collection: **what score does an answer with
no content in it already get?**

A scorer in Inspect is an async function of a `TaskState` and a `Target`. It does
not care whether a model produced the completion. So the eval's own scorer is
driven over the eval's own dataset with a battery of completions that carry no
information about the sample. No model is called. The sweep costs nothing and is
deterministic.

---

## 3. Battery membership, and the rendering rule

Fixed. **Eight content-free members and two reference baselines. No member is
added or removed to accommodate any task.**

Each member is defined **semantically** -- by what it *is*, not by the exact
characters it consists of. `all_labels` is "every distinct target in the
dataset". `majority` is "the modal target". A semantic value then has to be
written down, and how it is written down is the rendering rule below.

### Content-free members

| member | semantic value | kind |
|---|---|---|
| `empty` | the empty string | literal |
| `whitespace` | a single newline | literal |
| `refusal` | `I'm sorry, but I can't help with that.` | literal |
| `all_labels` | every distinct target in the dataset | label-valued |
| `all_letters` | the option letters `A B C D E`, bare | literal |
| `echo` | the sample input, echoed back verbatim | literal |
| `boilerplate` | a 571-character fluent paragraph with no task content | literal |
| `format_only` | the answer template with the placeholder `A` | template |

### Reference baselines

| member | semantic value | kind |
|---|---|---|
| `majority` | the modal target of the dataset | label-valued |
| `uniform` | a target drawn uniformly from the label set, averaged over seeds 0-4 | label-valued |

### The rendering rule

**A member's semantic value is written down in the task's declared answer
template when the task declares one. Both forms are scored and both are
reported.**

| arm | what it is |
|---|---|
| `raw` | the semantic value written plainly, ignoring any template |
| `rendered` | the semantic value written in the task's own answer template |

**The flag rule uses the `rendered` arm.**

Only **label-valued** members and `format_only` are affected. `literal` members
are never templated in either arm, because dressing `boilerplate` in `ANSWER:`
would invent a different member rather than render this one.

The one template Inspect declares structurally rather than in prose is multiple
choice, detected by the sample carrying `choices`:

| member | raw on a choice task | rendered on a choice task |
|---|---|---|
| `all_labels` | `A B C D` | `ANSWER: A, B, C, D` |
| `majority` | `C` | `ANSWER: C` |
| `uniform` | `B` | `ANSWER: B` |
| `format_only` | `ANSWER: A` | `ANSWER: A` |

On every other task in the first sweep -- `includes`, `match`, `pattern`, `f1` --
no template is declared and rendering is the identity, so the two arms are
**identical by construction**. That includes `paws`, and it is asserted as a
test: the 8000/8000 anchor cannot have come from a choice about templates.

**Why rendering is not cheating.** `ANSWER: A, B, C, D` names every option and
says nothing whatever about the sample, exactly as `"No Yes"` does on `paws`. It
adds no task content. What it adds is legibility: a multiple-choice scorer does
not read completion text at all, it reads which choices the `multiple_choice()`
solver marked, and that solver marks nothing unless it sees `ANSWER: X`. An
unrendered baseline on such a task is not a plainly-expressed answer, it is an
unreadable one, and it scores zero for a reason that has nothing to do with the
eval's validity.

### Definitions that would otherwise be left to run-time choice

* **`all_labels` ordering** is by descending frequency, ties broken
  lexicographically. Joined by a single space when raw, by `", "` inside the
  template when rendered. On `paws` the member is the constant string `"No Yes"`
  in both arms.
* **The `refusal` string contains neither "yes" nor "no" as a substring.**
  Deliberate and conservative. Common refusals do -- "I don't know" hides "no"
  inside "know", "cannot" contains it outright -- and either would score on every
  yes/no `includes()` task by accident. A clean phrasing means a `refusal` flag
  says the scorer is loose, not that the sentence was rigged.
* **`uniform` is seeded by `(seed, sample id)`**, so the draw is reproducible.
* **Samples are sorted by id before any `--limit` is applied.** `paws` and
  `boolq` both shuffle unseeded, so without this a limited sweep takes a
  different subset every run (instrument defect 004).

### What counts as a label set

`all_labels` and `uniform` are undefined on free-text targets. A dataset has a
**closed label set** when all three hold:

* at most **50** distinct targets,
* every target at most **100** characters,
* strictly fewer distinct targets than samples.

Fail any one and those two members are recorded `n/a` with the reason, rather
than given a made-up value. `majority` is still computed: the modal target of a
free-text dataset is a real, if small, chance line.

---

## 4. The flag rule

> **A task is flagged when at least one content-free battery member, in the
> `rendered` arm, scores at or above that task's own `majority` baseline, and
> that member's score is strictly greater than zero.**

`majority` is computed per task from that task's own dataset. It is never
assumed. The PAWS test split is 55.8 per cent `No`, so its chance line is 0.558
and not 0.5.

The **strictly greater than zero** clause is not decoration. When a scorer cannot
be driven at all, everything scores zero including `majority`, and every
content-free member then satisfies `0 >= 0` -- so the task reports as flagged by
the entire battery at 0.0 per cent each. That is a defect signature, not a
finding. It happened (`sec_qa_v2`, instrument defect 002) and it is pinned as a
test.

**Primary number.** Flagged reachable tasks over reachable tasks, with the
denominator stated before the result.

**Secondary numbers.** The same rate on the `raw` arm; the highest score any
content-free member reached per flagged task; the distribution of that maximum
across reachable tasks; the share of flagged tasks whose scorer is `includes()`
or `match()` against a natural-language target; and the gap between `majority`
and the best content-free member per task.

---

## 5. Coverage rules

A task is **reachable** when the deterministic sweep can run it on one laptop
with no container, no credentials and no grader model. Every task that is not
reachable gets a row in `results/coverage.md` with one of these reasons. Counts
are generated, from the installed `inspect_evals` 0.20.0.

| reason | tasks | rule |
|---|---|---|
| `sandbox_required` | 76 | the task declares a sandbox, ships a Dockerfile or compose file, or its scorer executes in one |
| `extra_dependency` | 49 | `eval.yaml` declares `isolated: true` or a `dependency` group that is not installed |
| `model_graded` | 27 | the scorer needs a grader model; deferred to the graded arm |
| `network_required` | 17 | assets of type `git_clone`, `direct_url` or `git_dependency`, or a scorer that fetches at score time |
| `gated_dataset` | 7 | the Hugging Face API reports the dataset as gated |
| `too_large` | 3 | Hub repository exceeds the disk cap |

**Reachable: 58 of 237 declared tasks.** That denominator is a result in its own
right and is published as prominently as the flag rate. `results/coverage.md`
carries **one row per declared task** -- 237 rows -- and prints that count, so a
reader can check that nothing was silently dropped.

**Disk cap: 1.00 GiB per dataset**, measured as the size of the dataset's Hugging
Face repository from the Hub tree API. That over-counts, since an eval usually
loads one split of several, so it is a conservative upper bound and the file says
so. It currently excludes `docvqa` (11.27 GiB), `mmmu` (3.40 GiB) and `mathvista`
(1.63 GiB).

**Gating is detected before downloading**, from Hub metadata, not by attempting a
download and catching the failure. Any task gated only at download time is
recorded as `load_error` with the exception verbatim.

**Exclusions are re-derived, never hand-maintained.**

---

## 6. The twenty tasks of the first sweep

**Selection rule**, applied by `discover.first_sweep_tasks()` rather than typed:

1. Start from reachable tasks whose scorer is one of the simple deterministic
   Inspect builtins: `includes`, `match`, `exact`, `pattern`, `choice`, `answer`,
   `f1`.
2. Rank by dataset sample count ascending, ties broken by task name.
3. Skip a task once its eval directory already has **two** entries. Without this
   cap, near-duplicate variants (`sec_qa` v1/v2 x 0-shot/5-shot, `wmdp` x 3,
   `mmlu` 0/5-shot) take a third of the slots and the twenty rows are far more
   correlated than they look.
4. Take the first twenty.

The rule was written before the list was read, and it lands `paws` and `boolq` --
the two evals named in issue #2331 and PR #2334 -- without either being forced in.

| # | task | scorer | dataset samples | hub repo size |
|---|---|---|---|---|
| 1 | `inspect_evals/vstar_bench_spatial_relationship_reasoning` | `choice()` | 76 | 362.6 MiB |
| 2 | `inspect_evals/sec_qa_v2` | `choice()` | 100 | 0.1 MiB |
| 3 | `inspect_evals/sec_qa_v2_5_shot` | `choice()` | 100 | 0.1 MiB |
| 4 | `inspect_evals/vstar_bench_attribute_recognition` | `choice()` | 115 | 362.6 MiB |
| 5 | `inspect_evals/musr` | `choice()` | 250 | 6.8 MiB |
| 6 | `inspect_evals/pre_flight` | `choice()` | 300 | 0.1 MiB |
| 7 | `inspect_evals/onet_m6` | `choice()` | 397 | 1.6 MiB |
| 8 | `inspect_evals/wmdp_chem` | `choice()` | 408 | 1.3 MiB |
| 9 | `inspect_evals/pubmedqa` | `choice()` | 500 | 286.6 MiB |
| 10 | `inspect_evals/truthfulqa` | `choice()` | 817 | 0.5 MiB |
| 11 | `inspect_evals/arc_challenge` | `choice()` | 1,172 | 1.2 MiB |
| 12 | `inspect_evals/commonsense_qa` | `choice()` | 1,221 | 1.5 MiB |
| 13 | `inspect_evals/winogrande` | `choice()` | 1,267 | 4.4 MiB |
| 14 | `inspect_evals/wmdp_bio` | `choice()` | 1,273 | 1.3 MiB |
| 15 | `inspect_evals/gsm8k` | `match(numeric=True)` | 1,319 | 5.6 MiB |
| 16 | `inspect_evals/arc_easy` | `choice()` | 2,376 | 1.2 MiB |
| 17 | `inspect_evals/boolq` | `pattern('(Yes\|No).?\\Z')` | 3,270 | 4.7 MiB |
| 18 | `inspect_evals/race_h` | `choice()` | 3,498 | 79.2 MiB |
| 19 | `inspect_evals/paws` | `includes()` | 8,000 | 123.3 MiB |
| 20 | `inspect_evals/drop` | `f1(extract_answer)` | 9,535 | 11.1 MiB |

**Totals: 35,994 samples, 1.23 GiB of Hub repositories** (an upper bound). Five
scorer families: `choice` x 16, `match`, `pattern`, `includes`, `f1` x 1 each.

**Failure rule -- no substitution in this sweep.** Any of the twenty that fails at
run time is recorded in `results/coverage.md` with its reason, and **the
denominator shrinks and says so**. Nothing is substituted in its place: the
harness has no substitution logic, and a rate quoted over "twenty" while one of
the twenty was quietly swapped for a reserve is a rate over a set the reader
cannot reconstruct. The reserves are published here, in order, so that a later
sweep can extend the set deliberately rather than silently: `hellaswag`,
`squad`, `mmlu_pro`, `mmlu_0_shot`, `mmlu_5_shot`.

---

## 7. Controls

| control | what it is | must show | status |
|---|---|---|---|
| Positive, real | `inspect_evals/gsm8k`, `match(numeric=True)` | every content-free member at or under 5%, on both arms | passing |
| Positive, fixture | `tests/fixtures/loose_eval.py::exact_numeric` | every content-free member at exactly zero | passing |
| Synthetic negative | `tests/fixtures/loose_eval.py::loose_refusal`, `includes()` over the labels "refusal" / "compliance" | flagged, `all_labels` at 100% | passing |
| Legitimate substring | `tests/fixtures/loose_eval.py::tight_flags`, the **same** `includes()` scorer over CTF-style flag targets | **not** flagged | passing |
| Determinism | two sweeps of the five-task smoke set | identical digest | passing |
| Chance line | `majority` and `uniform` computed per task | never a global assumption about label balance | passing |
| Anchor | `tests/test_paws_regression.py` | `all_labels` at 8000 of 8000 on `paws` | passing |

The `tight_flags` control is the one that earns the flag rule its keep. It uses
the identical `includes()` scorer as the flagged fixture and is **not** flagged,
because its targets are the ground truth rather than natural-language property
names. The rule is about the floor under a task, not about which scorer name
appears in its source.

Instrument defects go in `INSTRUMENT_LESSONS.md` with the date caught and what
they invalidated, rather than being quietly fixed. Eight are logged so far.

---

## 8. Decisions -- accepted 2026-09-17, before this file was committed

**How to accept:** for each item you agree with, delete the word "proposed";
where you decide differently, write what you chose and why in place of the
recommendation. Then rename this file to `PREREGISTRATION.md` and commit it. The
commit is the timestamp the whole method rests on, and `evalfloor sweep` refuses
to produce a result until it exists.

Each is **decided**, with the alternative it was chosen over.

### 8.1 The denominator counts `inspect_evals/*` tasks only

**Decided 2026-09-17: accepted.** Tasks defined in this repository -- `evalfloor/control_*` and
`evalfloor_fixtures/*` -- are instruments, not subjects. They must never enter
the published rate, or the synthetic negative control would inflate it by
construction.

*Alternative:* leave it implicit, as it is today (the sweep takes its task list
from the generated inventory, which contains only `inspect_evals/*`). Rejected
because "nothing enforces it" is how a number goes wrong six weeks later.

### 8.2 Members are rendered in the task's answer template; both arms published

**Decided 2026-09-17: accepted, and already implemented** so that the effect could be measured
before being argued about. Every member is defined semantically and written down
in the task's declared answer template when it declares one. Both the `raw` and
the `rendered` arm are scored, and the flag rule reads `rendered` (section 3).

Three reasons to prefer this over the alternatives:

1. **It is not a new member.** The battery stays at eight content-free members.
   The earlier suggestion -- adding a format-aware `all_labels` variant -- would
   have changed battery membership after the fact, which is exactly what a
   preregistration exists to prevent.
2. **It removes a special case rather than adding one.** The first fix for
   instrument defect 003 reformatted only the two reference baselines. That left
   two members inside the template and six outside, for no reason a reader could
   check. Special cases in a measurement definition are where bias hides.
3. **The effect is a published number, not a claim.** In the five-task smoke set,
   four tasks declare no template and their arms come out byte-identical; the
   arms disagree on exactly one task, and they disagree the *opposite* way from
   the obvious reading -- the raw arm flags `sec_qa_v2` and the rendered arm does
   not, because a bare label cannot parse there, so `majority` collapses to 0.0
   per cent and almost anything clears it.

**What it does to the headline, measured rather than guessed:** rendering
`all_labels` as `ANSWER: A, B, C, D` scores **0.000** on a `choice()` task.
`parse_answers` rejects a multi-option answer to a single-answer question. So
`choice()` is genuinely tight against "name every label", and since 16 of the 20
first-sweep tasks use `choice()`, this decision most likely *lowers* the flag
count rather than raising it. That is the opposite of what yesterday's draft
feared, and it is worth knowing before the sweep rather than after.

*Alternatives rejected:* (a) render nothing, which reproduces instrument defect
003 and flags multiple-choice tasks for an artifact; (b) render only the
reference baselines, which is the special case described above.

### 8.3 Keep the two `vstar_bench` multimodal tasks in the twenty

**Decided 2026-09-17: accepted, with a caveat rather than a removal.** The selection rule put them
there; removing them by hand would make the rule decorative. If they fail at run
time the substitution rule already handles it and records why.

The caveat belongs in the limitations table either way: `echo` is not well
defined on image inputs, so on those two tasks it measures something closer to
"the text scaffolding around an image" than "the input".

*Alternative:* drop them for exactly that reason and bring in `hellaswag` and
`squad` from the reserves. Defensible, and it would add `exact()` coverage via
`squad`'s `[f1(), exact()]`. If Ebin prefers a stated reason over rule-purity,
take this one.

### 8.4 Disk cap stays 1.00 GiB, measured as Hub repository size

**Decided 2026-09-17: accepted.** It over-counts, which is the safe direction for a cap, and it is
cheap: one metadata request, no download. The three tasks it excludes are
excluded by a wide margin (11.27, 3.40 and 1.63 GiB), so a tighter measure would
not change the membership.

*Alternative:* measure the split actually loaded. More accurate, but the Hub API
does not give it cheaply, and it would mean downloading in order to find out
whether to download.

### 8.5 NEW -- `format_only` can collide with `majority` by construction

**Found while implementing 8.2. Decided 2026-09-17: accepted as recommended,
in both halves -- the tie rule stays exactly as written, and any flag that
rests only on this collision is marked, never silently counted.**

On a multiple-choice task whose modal target happens to be `A`, `format_only`
(`ANSWER: A`) and `majority` (`ANSWER: A`) are *the same completion*. They score
identically, the `>=` in the flag rule fires on the tie, and the task is flagged
for a definitional collision rather than a finding.

**The rule, as decided:** keep the flag rule as it is -- a tie flags, that is
what "at or above" means, and weakening it after seeing data is worse -- and have
`report.py` mark any flag whose only flagging member is `format_only` **and** whose
completion string equals `majority`'s. Record a `note` ruling in `rulings.jsonl`
for each such task, so the collision is visible in the published rate instead of
silently inflating it. Both halves are live. The mark is computed in
`aggregate.py` as a `collision` field on each floor, set when the only flagging
member is `format_only` **and** the completion string it was scored on is the
completion string `majority` was scored on; the matrix carries a `collision`
column with a per-task note, the README's flag line reads "N flagged, of which K
rest on the template collision", and a committed fixture
(`evalfloor_fixtures/template_collision`) fails the suite if a collision stops
being marked. The flag rule itself is untouched.

*Alternative:* exclude `format_only` from the flag rule on tasks whose modal
label is the placeholder. Rejected: that is a rule which changes its behaviour
based on the data it is measuring, which is the shape of the problem rather than
the fix.

This was the one open item that could have changed a number in the twenty-task
sweep; it is now decided, and it changes the marking of a flag, not the flag
rule itself.

---

### 8.6 The judge default is luna, not nano -- and the tier is standard

**Decided 2026-09-17: accepted** -- luna at standard tier as the default judge,
nano as fallback, `z-ai/glm-5.3-flash` pinned to DeepInfra as the cross-family
second grader, and the disagreement control run before any graded number is
quoted.

**Measured 2026-09-15, contradicting the cost plan's projection.**

The plan picks `gpt-5-nano` as judge on list price (4x cheaper input, 3x cheaper
output than `gpt-5.6-luna`). Measured on a real 140-call smoke of the same task
with the same battery:

| judge | in/call | out/call | full 8-task arm at flex |
|---|---|---|---|
| `gpt-5-nano` | 277 | **1,157** | **$1.91** |
| `gpt-5.6-luna` | 273 | **87** | **$0.63** |

nano emits **13x more output tokens per grading call** because it reasons before
answering, and output is the expensive side. The per-token prices in the plan are
right; the assumed token shape (250 out) is not, and the ranking inverts.

**Decided 2026-09-15: `gpt-5.6-luna` is the default judge, `gpt-5-nano` the
fallback.** Cheaper on measured shape, faster, and the model named in the
complimentary daily-token group for tiers 1-2 (nano's inclusion there is
unverified). nano stays selectable with `EVALFLOOR_JUDGE`.

**Also decided: service tier `standard`, not flex.** Flex is 50% off and about
4 calls/min against standard's measured 12.7, which on the 8,000-call arm is
~33 hours versus ~10.5, for about $0.60. Flex stays available behind
`--tier flex`, and every run prints its projected wall clock before starting.

Second, and larger: the two judges **disagree substantially** on the same task
(luna put `majority` at 0.0% and flagged 2 members; nano put it at 20.0% and
flagged 3). Whichever judge is chosen, the disagreement control must run before
any graded number is quoted.

Measured cross-lineage disagreement, luna against `z-ai/glm-5.3-flash` pinned to
DeepInfra, same 10 samples: **13 of 111 = 11.7% [7.0, 19.0]**
(`results/smoke/graded/sweep.json`, `disagreement` block). About one graded cell
in nine flips on a change of judge, so every graded number carries at least that
much slack. Notably smaller than the luna-vs-nano spread, which points at nano's
verbosity rather than genuine cross-lineage disagreement.

An earlier reading of this control gave 10 of 105 = 9.5% [5.3, 16.6]. It is
superseded rather than wrong: it was measured while the DeepInfra pin was being
sent through a channel the client overwrote, so the pin did not take effect and
nothing recorded which provider served those 140 second-grader calls
(instrument defect 008). The arm above is a fresh 140 cells with the pin in
effect and the serving provider read back **once per task**, at the start of the
run, and stamped on every row of it; `attribute_provider` then reconciles that
reading against the per-row counts, and reports nothing when neither has anything
to say. The two arms differ in the
serving provider and in ordinary run-to-run variation of a non-deterministic
grader, and this design cannot separate the two; their intervals overlap across
most of their range, so the change is not evidence that routing moved the rate.

---

## 8A. The model-graded arm

A separate arm with separate rules, and its rate is **never added to the
deterministic arm's**. One is exact over whole datasets and free; the other is a
capped sample graded by a model that can be wrong and costs money per call. A
combined "N of M" across both would be a number with no meaning.

### Which tasks

The **27** tasks the generated inventory classifies as `model_graded` -- their
scorer needs a grader model. That list is re-derived by `evalfloor inventory`,
never hand-maintained.

The **eight** below are not re-derived. They are named in the code as
`GRADED_FIRST_SWEEP` in `cli.py`, in the order this section lists them, and
passed to the graded arm explicitly; a test fails if the two lists disagree.
Naming them is the point: the arm used to fall back to all 27, which is nine
URL-fetching `agie_*` tasks, a 3.41 GiB download and a gated dataset.

Of those 27, checked against Hub metadata on 2026-09-15 without downloading
anything, **8 are runnable**: `frontierscience`, `moru`, `fortress_adversarial`,
`fortress_benign`, `mask`, `coconot`, `uccb`, `sosbench`. The other 19 are
excluded and counted:

| reason | tasks |
|---|---|
| dataset is not on the Hugging Face Hub (fetched from a URL or a repo at run time, or shipped inside the installed package) | 16 |
| dataset over the 1.00 GiB cap (`mmmu_open` 3.41 GiB, `cyse3_visual_prompt_injection` 1.17 GiB) | 2 |
| gated dataset (`xstest`) | 1 |

An earlier draft of this table carried a fourth row, "loads, but needs an
optional provider dependency (`moru`)", which contradicted `moru` appearing in
the runnable eight two paragraphs above. Checked at run time on 2026-09-17 rather
than from the note: `moru` has **no** optional provider dependency -- its whole
import closure is in the base install -- and it loads, resolves and grades. What
it had was a harness defect. It declares
`grader_models: list[str | Model] | None = None`, so the judge injection, which
read the shape off the default, handed it a bare `Model` and the scorer raised
`TypeError: 'Model' object is not iterable` *after* its dataset had downloaded.
The injection now reads the annotation when the default is None. `moru` stays in
the eight, the row is gone, and the "not on the Hub" row absorbs the task that
row had been miscounting.

**The graded denominator is 8, not 27**, and the write-up says so before it says
anything else -- the same discipline as the deterministic arm's 58 of 237. It is
8 *tasks attempted*; a task that fails at run time is recorded in
`results/graded/coverage.md` with its reason and leaves the denominator, exactly
as in section 6, and nothing is substituted for it.

### The grader -- fixed fields

One cheap judge, recorded in every row together with the snapshot the provider
served. The snapshot is the model id read off the **first response** of the run
(Inspect's `ModelOutput.model`); when no provider reported one -- a run answered
entirely from cache reports none -- the field carries the requested id followed
by `(requested; the provider reported no model id)`, so a request can never be
read as a response. Key order is **OpenAI, then OpenRouter**. Anthropic is not a
judge for this arm at all.

| field | value |
|---|---|
| **judge** | `openai/gpt-5.6-luna`, **service tier `standard`** -- $0.20 in / $0.02 cached / $1.20 out |
| **fallback** | `openai/gpt-5-nano` -- $0.05 / $0.005 / $0.40; used only if luna is not served, and selectable deliberately with `EVALFLOOR_JUDGE` |
| **second grader** | `openrouter/z-ai/glm-5.3-flash`, **pinned to the DeepInfra endpoint** -- $0.075 / $0.25 |
| alternative second | `openrouter/deepseek/deepseek-v4.1-flash` -- $0.15 / $0.60 |
| **excluded as judge** | `claude-haiku-4-5` -- naming it **raises**; 14x the nano arm, and nothing caches at its 4,096-token minimum |
| price and id source | `decision-2026-09-15/F-economy-plan.md` section 1 workload 1 (2026-09-15), ids cross-checked against Kobayashi Maru's `dosecurve/analysis/prices.json` (2026-09-13) and `harness/providers/openai_compat.py` |
| overrides | `EVALFLOOR_JUDGE`, `EVALFLOOR_JUDGE2` |

**Why luna and not nano**, despite nano being 4x cheaper per input token: nano
emits **about 13x more output per grading call** (1,157 vs 87 tokens, measured),
and output is the expensive side, so nano is roughly **3x dearer** for this arm.
luna is also the model named in the complimentary daily-token group for tiers
1-2; nano's inclusion there is unverified.

**Why standard tier and not flex**, despite flex being 50% off: flex runs at
about **4 calls/min** against standard's measured **12.7**. On the 8,000-call arm
that is roughly **33 hours against 10.5**, to save about $0.64. Flex remains
available behind `--tier flex` for runs where time is free, and every run prints
its projected wall clock before it starts.

**Judge injection.** The judge is injected through each task's own grader
parameter, not through `INSPECT_EVAL_MODEL`: every model-graded task takes its
judge as a task argument defaulting to a hard-coded provider model, so the
environment variable alone does not redirect it (instrument defect 006). A task
exposing no such parameter is reported `NOT REDIRECTABLE` rather than silently
graded by whatever it hard-codes.

**Provider pinning is requested, and the serving provider is now recorded per
call.** The request carries `provider: {order: ["DeepInfra"],
allow_fallbacks: false}`, and unpinned the same weights bill at roughly double.
Every row in `results/smoke/graded/graded_cache.jsonl` carries a
`served_provider` field read from OpenRouter's own response rather than inferred
from the request, and it reads `unreported` when it could not be read. On the
second-grader smoke, **136 of 140 calls record `DeepInfra`**; the other 4 record
`unreported`, which is a hole in the record and not another provider. Because
`allow_fallbacks: false` is set, a call served by anyone else would have failed
rather than been billed at the canonical rate.

Until 2026-09-16 the pin was requested through `extra_body`, which Inspect's
OpenRouter client builds itself and overwrites, so **the pin never took effect
and nothing recorded who served those calls** (instrument defect 008). Every
second-grader cost figure measured before that date was measured under
unrecorded routing and may have been paid at the canonical rate. The pin is now
passed as a model argument, which is the channel that client reads.

### Prompt caching

| provider / model | caching | cached input price |
|---|---|---|
| `openai/gpt-5.6-luna` | automatic, prefix-matched, 1,024-token minimum | **$0.02 /MTok** (against $0.20 uncached) |
| `openai/gpt-5-nano` | same | **$0.005 /MTok** (against $0.05) |
| `openrouter/z-ai/glm-5.3-flash` | automatic, per model, no `cache_control` needed | cache writes currently free; the read price is not verified by this project |
| `claude-haiku-4-5` | 4,096-token minimum | n/a -- excluded as judge |

Where eval-floor supplies the grading template, the static part (instructions,
then that eval's grade vocabulary) goes **first** and the sample **last**,
because caching is prefix-matched and a sample-first prompt never hits.

**Measured, and it is zero.** On the real smoke OpenAI reported **0 cached tokens
across 140 calls**: the static prefix is about **275 tokens against a
1,024-token minimum**, so caching was never possible. That is arithmetic, not a
fault, and the estimator no longer banks a saving it cannot get.

**The rubric is deliberately not padded to cross the minimum.** A longer rubric
that crossed 1,024 would be cheaper per call, but filler added to win a discount
changes what the judge is asked, and a harness that edits the question to save
money has stopped measuring the thing. Instead: calls are grouped by task and run
as one consecutive stream, `prompt_cache_key` is set per task, `cached_tokens` is
logged on every call, and the abort guard fires **only** when a prompt that
*should* cache returns zero -- never on one that was always too short.

### Per-eval grade vocabulary -- fixed field

Graded evals answer in their own vocabularies. `coconot` returns
ACCEPTABLE / UNACCEPTABLE / NEITHER; its contrast subset returns
NONCOMPLIANCE / COMPLIANCE / NEITHER; Inspect's generic `value_to_float()` knows
only C / P / I / N and returns **0.0** for anything else.

That default silently discards credit, in the direction that **understates** a
floor. The eval's own converter is not reachable from the built `Task`, so the
mapping is a judgement call, handled the way this project handles every
judgement call: **`verdict_maps.jsonl`, one row per eval, each quoting the eval
source line it was read from**, applied mechanically.

**A verdict with no committed mapping is never coerced to 0.0.** It is recorded
verbatim as an `unmapped_verdict`, excluded from the denominator, and its
distribution is printed. Adding a mapping is a commit with a source line in it,
never a run-time guess.

**The judge is injected through each task's own grader parameter**, not through
`INSPECT_EVAL_MODEL`. Every model-graded task in the collection takes its judge
as a task argument defaulting to a hard-coded provider model, so the environment
variable alone does not redirect it (instrument defect 006). A task exposing no
such parameter is reported `NOT REDIRECTABLE` rather than silently graded by
whatever it hard-codes.

### The cap, and the arms

**100 samples per task per member**, taken after sorting by sample id.

Only the **rendered** arm is paid for on a task that declares no answer template:
there the two arms are identical by construction, and the deterministic sweep
already demonstrates that on every such task at zero cost. Tasks that do declare
a template get both arms. The report states which arms ran and why.

### The flag rule on this arm -- stricter than the deterministic one

> A graded task is flagged when at least one content-free member's **Wilson 95%
> lower bound** reaches that task's `majority` baseline, and its score is
> strictly greater than zero.

The lower bound, not the point estimate. Over 100 sampled items a point estimate
would flag on sampling noise, and this is the arm where a false flag is the most
expensive to defend.

**No graded rate is ever reported bare.** Every figure carries its interval.

### Three outcomes, not two

Every grading call ends in exactly one of:

| outcome | counted as | in the denominator? |
|---|---|---|
| **graded** | the score the grader gave | yes |
| **refused** | the grader or the provider declined | **no** |
| **ungradeable** | the grader answered but emitted no parseable grade | **no** |

Neither a refusal nor an ungradeable response is scored as zero. Counting a
declined grading as a failed answer would quietly credit the battery member it
was grading; coercing an unparseable grade to zero would report a floor that was
never measured (instrument defect 006).

A task where **nothing** scored reports `NO RESULT`, never `0.0%`, and is kept
out of the flag-rate denominator entirely.

### Refusals are data

Every refusal is appended to `refusals.jsonl` with its verbatim text, a SHA-256
of the prompt that produced it, the grader, and whether it was retried. **The
prompt is hashed, not stored.** Refusals are never reworded and never retried
beyond **one identical retry** -- no rephrasing to coax an answer out, because a
grader that has to be coaxed is not measuring the same thing any more.

### Caching

Every result is cached to disk, keyed by task, scorer, sample id, member, seed,
arm, grader model and battery fingerprint. A rerun costs nothing and an
interrupted run resumes. Changing any of those keys is a different measurement
and misses the cache, which is the point of keying on all of them.

### The judge-disagreement control

**One full task at the 100-sample cap** is run with a second grader from a
different lineage -- `openrouter/z-ai/glm-5.3-flash` against the OpenAI judge --
and the disagreement rate is reported with its interval. Compared **per item**,
not per mean: two judges can agree on every mean while disagreeing on every item.

**The control task is `inspect_evals/coconot`**, fixed here and defaulted in the
code as `--disagreement-task` (`evalfloor graded --disagreement-task`). The prior
below was measured on that task and on no other, so a control run anywhere else
would answer a different question under the same field name. When the named task
is not in the run's task list the control is **skipped, with the reason printed
and serialised**, never moved to whichever task happens to sort first.

That rate is how much of this arm is judge noise rather than signal, and it is
published beside the arm's headline, not in a footnote.

**Measured prior, from the 10-sample smoke on `coconot`: 13 of 111 comparable
cells = 11.7% [7.0, 19.0].** The other **29** of the 140 cells are *uncomparable*
-- all 29 because one grader or the other refused -- and are counted and printed
as such rather than compared as zeros. A cell with no finite value is not a cell
that scored zero, and reading one as the other would make two graders that both
declined look like two graders that agreed. About one graded cell in nine flips on
a change of judge. Treat it as an **order-of-magnitude figure only** -- one task, ten
samples, and a wide interval. The preregistered control replaces it with one full
task at the cap.

For contrast, the same battery judged by `gpt-5.6-luna` and by `gpt-5-nano` put
the `majority` line at 0.0% and 20.0% respectively. That within-vendor spread is
*larger* than the cross-lineage one, which points at nano's verbosity rather than
at genuine lineage disagreement -- and is a second reason the judge is fixed
before the arm runs.

### Cost, and the guard

The estimate and the **projected wall clock** are printed **before** any provider
call, and the run refuses when the estimate exceeds `--budget-usd` (default $5
for a smoke run, $30 for the real arm). The guard fires at **two** levels, and
both are checked before anything is called. The whole arm's estimate is summed
first, over every task in the run's list, and the run refuses if that total
exceeds the budget; then each task's own estimate is checked again against the
same budget before that task's first call. The per-task check alone was not
enough: eight tasks each comfortably under the budget can spend eight times it.

Measured token shape for the judge, from the real smoke: **273 in / 88 out per
call**. Over 8,000 calls that is **2.19M input / 0.70M output**.

| configuration | cost | wall clock |
|---|---|---|
| **luna, standard tier -- the default** | **$1.28** | **~10.5 h** |
| luna, flex tier | $0.64 | ~33.3 h |
| glm-5.3-flash second pass over all 8 tasks, pinned | +$0.34 | -- |
| **recommended: standard + one-task disagreement control** | **$1.32** | ~10.5 h |

**The $30 guard sits far above the $1.32 estimate, by design.** It is not a
forecast; it is the ceiling that stops a loop, a retry storm or a mis-set cap
from turning a $1 arm into a $100 one. A guard set close to the estimate would
fire on ordinary variance and teach the operator to raise it, which is how a
guard becomes decoration.

**OpenAI usage may be complimentary** under the org's data-sharing setting, in
which case the true cost is lower. It is **not** assumed to be zero anywhere:
every figure above is list price. Nothing from `profile-update-aug2026` is ever
sent through these keys -- the only content leaving this machine is Inspect Evals
dataset samples and the battery's own fixed strings.

### The `coconot` ruling template

`rulings.jsonl` carries a `note` row for `inspect_evals/coconot`. It was
written commented-out and deliberately inert -- `load_rulings()` skips every
line that starts with `#`, and that skip is the whole guarantee; no test pins
it -- and it was uncommented on 2026-09-17, before any result existed, as this
section directs.

Its substance: coconot grades **contextual** noncompliance, so on part of that
dataset a content-free or non-answering completion **is** the behaviour the eval
wants. A flag there does not mean "a content-free answer scores like a real one";
it means "a content-free answer reads as compliance to the judge". Those are
different claims and the write-up must not merge them.

**The rule, exactly: the flag rate for that task is reported both with and
without this ruling applied**, in the same table, so a reader sees the size of
the judgement call rather than its conclusion only.

### Negative result for this arm, stated in advance

**If fewer than three of the reachable model-graded tasks are flagged, the
finding is that model-graded scoring in this collection has no content-free floor
above chance, and the write-up says so in the graded arm's first paragraph.**

The threshold is three rather than five because the denominator is smaller (8,
not 58). It is fixed now and does not move after the numbers are in. A graded arm
that finds nothing is still worth publishing: it would mean the looseness found
in `paws` is a property of substring scorers rather than of eval scoring
generally, which is a more useful conclusion than a bigger number.

---

## 9. What this project does not claim

A flagged task is not a worthless benchmark. A loose scorer inflates a number
without saying the underlying task is easy. **No claim is made about the
conclusions of any published paper that used any of these evals.**

Issue #2331 is caiotheodoro's finding, opened 2026-08-31. This project
generalises it; it does not claim it. PR #2334 by jkopczyn fixes `paws` and
`boolq`; as of 2026-09-15 it is open, unmerged, carries no approving GitHub
review (a maintainer comment from MattFisher on 2026-09-09 calls it
"merge-ready"), and no release contains it.

The deliverable is the measurement and the gate. **No eval is fixed here, and no
issue is filed upstream from this week's work.**

---

## 10. Pins

`inspect_ai==0.3.263`, `inspect_evals==0.20.0`. Both recorded in every generated
results file alongside a battery fingerprint that covers the rendering rule. Rows
produced under one version pair are never mixed with rows from another: on any
bump, the whole sweep re-runs.


---

## 11. Close-out addendum -- 2026-10-10, written after the 17 Sep results existed and before any result on 0.24.0

Moves no threshold. Ruled by Ebin on 2026-10-10: `lab_bench` is counted.

1. **The countable list** is fixed by name in `cli.CLOSEOUT_TASKS`: 45 of the 58 tasks reachable on 0.20.0. These are the 20 of section 6, 8 more `choice()` tasks, 9 tasks with other deterministic scorers, and the 8 `lab_bench` tasks. The other 13 carry a `not_counted` row in `rulings.jsonl` with its reason and source line: 4 need solver state (`tau2_*`), 3 need a judge (`agentharm`, `agentharm_benign`, `vqa_rad`, whose open questions go to a grader), and 6 score behaviour, not answer correctness (`agent_threat_bench` x3, `air_bench`, `make_me_pay`, `stereoset`).
2. **`lab_bench`** is scored on its own `accuracy()`: an "Insufficient information" answer is NOANSWER and counts 0. Its `precision()` is printed beside it and never used for a flag.
3. **One release.** The list is swept whole on `inspect_evals` 0.24.0 with `inspect_ai` 0.3.263; 0.24.0 is the latest release on 2026-10-10. This supersedes the 20-task sweep on 0.20.0 (`316f142`), which stays in git. 0.20.0 stays installed only for the `paws` anchor test. The graded arm stays on 0.20.0, is not re-run, and carries its own pin. Arms are never added (section 8A), so no row mixes releases.
4. **No task is added.** A listed task that is absent or fails on 0.24.0 is "not run", with its error (section 6). Reachable tasks in the 0.24.0 inventory that are not on the list are named and not run.
5. **Thresholds are unchanged.** Section 1 stays at five, with ties counted and marked (section 8.5). Section 8A stays at three.
6. **Polarity** is recorded per graded task in `verdict_maps.jsonl`, each value with its source line; an inverted flag is never called credit.
7. **Determinism.**
   - Every task load runs with unseeded shuffles pinned to seed 42. For `hf_dataset` this is `seed=42, shuffle_choices=42`, the call upstream adopted in #2404 (`truthfulqa`) and #2406 (`lab_bench`) after 0.24.0.
   - The seed is stamped in every payload as `shuffle_seed` and in `run_fingerprint`. `battery_fingerprint` is unchanged.
   - The list runs twice, in separate processes. A task whose two runs differ, or that errors in only one, is "not run: non-deterministic".
8. **New flags.** A non-tie flag on 0.24.0 is traced to a source line and classified as a scorer defect, a task property or an instrument fault before anything is written about it. Only a scorer defect becomes an upstream issue.
9. **The banner.** The "DRAFT" banner at the top of this file is historical; its first commit was `912345f8d5be`.
