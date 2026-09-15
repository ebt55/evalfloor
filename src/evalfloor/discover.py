"""Enumerate every task in ``inspect_evals`` and classify what scores it.

Discovery is deliberately **static**. Calling a task function is what downloads
its dataset, so a dynamic inventory of 248 tasks would mean downloading the whole
collection before knowing which parts of it are even worth sweeping. Instead this
module reads the installed package: each eval's ``eval.yaml`` for its declared
tasks, sample counts and external assets, and the Python sources by ``ast`` for
the ``scorer=`` argument of every ``@task`` function.

Two axes come out of it.

*   **Scorer class.** ``deterministic`` (a scorer that is a pure function of the
    completion and the target: ``includes``, ``match``, ``exact``, ``pattern``,
    ``choice``, ``answer``, ``f1`` and custom scorers that call no model),
    ``model_graded`` (needs a grader model), ``sandbox`` (executes the completion
    in a container), ``network`` (fetches at scoring time), or ``unknown``.
*   **Reachability.** Whether the deterministic sweep can run the task at all on
    this machine, or whether it is excluded, with the reason recorded.

Nothing here downloads a dataset. The optional Hugging Face probe asks the Hub
API for a dataset's gated flag and its repository size in bytes, which is a
metadata request, not a download.
"""

from __future__ import annotations

import ast
import json
import pathlib
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Iterator

import yaml

# --------------------------------------------------------------------------
# Scorer vocabulary
# --------------------------------------------------------------------------

#: The builtin scorers that are pure functions of (completion, target). These are
#: "the simplest deterministic scorers" the first sweep is drawn from.
SIMPLE_DETERMINISTIC: frozenset[str] = frozenset(
    {"includes", "match", "exact", "pattern", "choice", "answer", "f1"}
)

#: Other inspect_ai builtins that need no model but are not simple string tests.
OTHER_DETERMINISTIC: frozenset[str] = frozenset(
    {"math", "precomputed_scores", "perplexity", "target_perplexity"}
)

#: Builtins that call a grader model.
MODEL_GRADED_BUILTINS: frozenset[str] = frozenset({"model_graded_qa", "model_graded_fact"})

#: Builtins that wrap other scorers; resolve through them.
COMBINATORS: frozenset[str] = frozenset({"multi_scorer", "cascade", "grouped", "aggregate"})

#: Identifiers whose presence in a custom scorer's body means a model is called.
MODEL_MARKERS: tuple[str, ...] = (
    "model_graded_qa",
    "model_graded_fact",
    "get_model",
    "grader_model",
    "judge_model",
    "scorer_model",
    "judge_llm",
    "expansion_llm",
    ".generate(",
    "GenerateConfig",
)

#: Identifiers whose presence means the scorer runs code in a sandbox.
SANDBOX_MARKERS: tuple[str, ...] = (
    "sandbox(",
    "sandbox_exec",
    "SandboxEnvironment",
    "ExecResult",
    "await sandbox",
)

#: Identifiers whose presence means the scorer reaches the network at score time.
NETWORK_MARKERS: tuple[str, ...] = (
    "httpx.",
    "requests.",
    "aiohttp",
    "urlopen",
    "urllib.request",
)

#: External asset types that mean the task fetches something at run time from
#: somewhere other than the Hugging Face Hub.
NONHF_ASSET_TYPES: frozenset[str] = frozenset({"git_clone", "direct_url", "git_dependency"})


# --------------------------------------------------------------------------
# Records
# --------------------------------------------------------------------------


@dataclass
class TaskInfo:
    name: str
    eval_id: str
    title: str = ""
    group: str = ""
    eval_version: str = ""
    dataset_samples: int | None = None
    registered: bool = False
    scorer_expr: str = ""
    scorer_bases: list[str] = field(default_factory=list)
    scorer_class: str = "unknown"
    scorer_detail: str = ""
    asset_types: list[str] = field(default_factory=list)
    hf_datasets: list[str] = field(default_factory=list)
    has_sandbox_files: bool = False
    declares_sandbox: bool = False
    isolated: bool = False
    dependency: str | None = None
    tags: list[str] = field(default_factory=list)
    reachable: bool = False
    exclusion_reason: str = ""
    exclusion_detail: str = ""
    hf_gated: bool | None = None
    hf_bytes: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------
# Locating the package
# --------------------------------------------------------------------------


def package_root() -> pathlib.Path:
    import inspect_evals

    return pathlib.Path(inspect_evals.__file__).parent


def registered_task_names() -> set[str]:
    """Registry names of every task ``inspect_evals`` exports."""
    from inspect_ai._util.registry import registry_find, registry_info

    import inspect_evals._registry  # noqa: F401

    return {registry_info(t).name for t in registry_find(lambda i: i.type == "task")}


# --------------------------------------------------------------------------
# Static parsing
# --------------------------------------------------------------------------


def _is_task_decorator(node: ast.AST) -> bool:
    src = ast.unparse(node)
    return src == "task" or src.startswith("task(")


def _call_base_names(expr: ast.AST) -> list[str]:
    """Every callable invoked anywhere inside a scorer expression.

    ``[aime_scorer()]`` -> ``["aime_scorer"]``;
    ``injection_task_scorer() if x else user_task_scorer()`` -> both;
    ``multi_scorer([a(), b()], "max")`` -> ``["multi_scorer", "a", "b"]``.
    """
    names: list[str] = []
    for node in ast.walk(expr):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                names.append(func.id)
            elif isinstance(func, ast.Attribute):
                names.append(func.attr)
    if not names:
        # a bare name, e.g. `scorer=scorer`
        for node in ast.walk(expr):
            if isinstance(node, ast.Name):
                names.append(node.id)
    seen: set[str] = set()
    ordered: list[str] = []
    for n in names:
        if n not in seen:
            seen.add(n)
            ordered.append(n)
    return ordered


def _resolve_local_name(fn: ast.FunctionDef | ast.AsyncFunctionDef, name: str) -> ast.AST | None:
    """Value last assigned to ``name`` inside ``fn``, if any."""
    found: ast.AST | None = None
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == name:
                    found = node.value
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == name and node.value:
                found = node.value
    return found


@dataclass
class _EvalSource:
    """Everything the AST pass learned about a set of Python files.

    ``func_scorer`` maps *any* function that constructs a ``Task(scorer=...)`` to
    that scorer expression -- not only ``@task`` functions. Many evals build the
    Task in a plain helper (``arc_task``) and have the ``@task`` function just
    call it, so resolution has to follow calls.
    """

    task_scorers: dict[str, str] = field(default_factory=dict)
    func_scorer: dict[str, str] = field(default_factory=dict)
    task_sandbox: dict[str, bool] = field(default_factory=dict)
    func_sandbox: dict[str, bool] = field(default_factory=dict)
    func_bodies: dict[str, str] = field(default_factory=dict)
    func_calls: dict[str, list[str]] = field(default_factory=dict)

    def merged_with(self, fallback: "_EvalSource") -> "_EvalSource":
        """This source's names win; the fallback fills the gaps."""
        out = _EvalSource(
            task_scorers=dict(self.task_scorers),
            func_scorer={**fallback.func_scorer, **self.func_scorer},
            task_sandbox=dict(self.task_sandbox),
            func_sandbox={**fallback.func_sandbox, **self.func_sandbox},
            func_bodies={**fallback.func_bodies, **self.func_bodies},
            func_calls={**fallback.func_calls, **self.func_calls},
        )
        return out

    def resolve_scorer(self, func_name: str, max_depth: int = 3) -> str:
        """The scorer expression for ``func_name``, following helper calls.

        Returns the empty string when no ``Task(scorer=...)`` is reachable.
        """
        seen: set[str] = set()
        frontier = [(func_name, 0)]
        while frontier:
            name, depth = frontier.pop(0)
            if name in seen or depth > max_depth:
                continue
            seen.add(name)
            expr = self.func_scorer.get(name)
            if expr:
                return expr
            for callee in self.func_calls.get(name, []):
                if callee not in seen:
                    frontier.append((callee, depth + 1))
        return ""

    def resolve_sandbox(self, func_name: str, max_depth: int = 3) -> bool:
        seen: set[str] = set()
        frontier = [(func_name, 0)]
        while frontier:
            name, depth = frontier.pop(0)
            if name in seen or depth > max_depth:
                continue
            seen.add(name)
            if self.func_sandbox.get(name):
                return True
            for callee in self.func_calls.get(name, []):
                if callee not in seen:
                    frontier.append((callee, depth + 1))
        return False


def _parse_files(paths: Iterable[pathlib.Path]) -> _EvalSource:
    out = _EvalSource()
    for py in paths:
        try:
            tree = ast.parse(py.read_text(encoding="utf-8", errors="replace"))
        except (SyntaxError, OSError, ValueError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            try:
                out.func_bodies.setdefault(node.name, ast.unparse(node))
            except Exception:
                pass
            calls: list[str] = []
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call):
                    if isinstance(sub.func, ast.Name):
                        calls.append(sub.func.id)
                    elif isinstance(sub.func, ast.Attribute):
                        calls.append(sub.func.attr)
            out.func_calls.setdefault(node.name, calls)

            is_task = any(_is_task_decorator(d) for d in node.decorator_list)
            for sub in ast.walk(node):
                if not isinstance(sub, ast.Call):
                    continue
                try:
                    func_src = ast.unparse(sub.func)
                except Exception:
                    continue
                if not func_src.endswith("Task"):
                    continue
                for kw in sub.keywords:
                    if kw.arg == "scorer":
                        value = kw.value
                        if isinstance(value, ast.Name):
                            resolved = _resolve_local_name(node, value.id)
                            if resolved is not None:
                                value = resolved
                        try:
                            expr = ast.unparse(value)
                        except Exception:
                            continue
                        out.func_scorer.setdefault(node.name, expr)
                        if is_task:
                            out.task_scorers.setdefault(node.name, expr)
                    elif kw.arg == "sandbox":
                        out.func_sandbox[node.name] = True
                        if is_task:
                            out.task_sandbox[node.name] = True
    return out


_PACKAGE_INDEX: _EvalSource | None = None


def package_index() -> _EvalSource:
    """AST index of every Python file in ``inspect_evals``, built once.

    Needed because shared scorers live outside the eval that uses them, e.g.
    ``aime_scorer`` in ``inspect_evals/utils/aime_common.py``.
    """
    global _PACKAGE_INDEX
    if _PACKAGE_INDEX is None:
        _PACKAGE_INDEX = _parse_files(sorted(package_root().rglob("*.py")))
    return _PACKAGE_INDEX


def parse_eval_dir(directory: pathlib.Path) -> _EvalSource:
    """Index one eval directory, with the whole package as the fallback scope."""
    return _parse_files(sorted(directory.rglob("*.py"))).merged_with(package_index())


def classify_scorer(bases: Iterable[str], source: _EvalSource) -> tuple[str, str]:
    """Return ``(class, detail)`` for a scorer expression's base callables."""
    bases = [b for b in bases]
    if not bases:
        return "unknown", "no scorer expression found"

    classes: set[str] = set()
    details: list[str] = []

    for base in bases:
        if base in COMBINATORS:
            continue
        if base in MODEL_GRADED_BUILTINS:
            classes.add("model_graded")
            details.append(f"{base}: inspect_ai builtin grader")
            continue
        if base in SIMPLE_DETERMINISTIC:
            classes.add("deterministic")
            details.append(f"{base}: inspect_ai builtin, pure function of completion and target")
            continue
        if base in OTHER_DETERMINISTIC:
            classes.add("deterministic")
            details.append(f"{base}: inspect_ai builtin, no model")
            continue

        body = source.func_bodies.get(base)
        if body is None:
            classes.add("unknown")
            details.append(f"{base}: custom, definition not found in this eval package")
            continue
        if any(marker in body for marker in SANDBOX_MARKERS):
            classes.add("sandbox")
            details.append(f"{base}: custom, executes in a sandbox")
        elif any(marker in body for marker in MODEL_MARKERS):
            classes.add("model_graded")
            details.append(f"{base}: custom, calls a grader model")
        elif any(marker in body for marker in NETWORK_MARKERS):
            classes.add("network")
            details.append(f"{base}: custom, reaches the network at score time")
        else:
            classes.add("deterministic_custom")
            details.append(f"{base}: custom, no model / sandbox / network marker found")

    if not classes:
        return "unknown", "; ".join(details) or "combinator only"
    # Worst case wins: a task that needs a model or a sandbox anywhere is not in
    # the deterministic arm, whatever else it also uses.
    for worst in ("sandbox", "network", "model_graded", "unknown"):
        if worst in classes:
            return worst, "; ".join(details)
    if classes == {"deterministic"}:
        return "deterministic", "; ".join(details)
    return "deterministic_custom", "; ".join(details)


# --------------------------------------------------------------------------
# Reachability
# --------------------------------------------------------------------------

#: Datasets larger than this on the Hub are excluded from the sweep and recorded.
#: Preregistered. 1 GiB, per the brief's disk cap.
MAX_DATASET_BYTES = 1024 * 1024 * 1024


def decide_reachability(info: TaskInfo) -> tuple[bool, str, str]:
    """``(reachable, reason, detail)``. First matching rule wins, in this order."""
    if info.scorer_class == "sandbox":
        return False, "sandbox_required", info.scorer_detail
    if info.declares_sandbox:
        return False, "sandbox_required", "task declares sandbox="
    if info.isolated:
        return False, "extra_dependency", "eval.yaml: isolated: true (separate package)"
    if info.dependency:
        return False, "extra_dependency", f"eval.yaml: dependency: {info.dependency}"
    if info.has_sandbox_files:
        return False, "sandbox_required", "eval directory ships a Dockerfile or compose file"
    if info.scorer_class == "model_graded":
        return False, "model_graded", info.scorer_detail
    if info.scorer_class == "network":
        return False, "network_required", info.scorer_detail
    nonhf = sorted(set(info.asset_types) & NONHF_ASSET_TYPES)
    if nonhf:
        return False, "network_required", f"external assets: {', '.join(nonhf)}"
    if info.hf_gated:
        return False, "gated_dataset", f"gated on the Hub: {', '.join(info.hf_datasets)}"
    if info.hf_bytes is not None and info.hf_bytes > MAX_DATASET_BYTES:
        gib = info.hf_bytes / (1024**3)
        return False, "too_large", f"{gib:.2f} GiB on the Hub, cap is 1.00 GiB"
    if info.scorer_class == "unknown":
        return False, "unclassified_scorer", info.scorer_detail
    if not info.registered:
        return False, "not_registered", "no entry in inspect_evals._registry"
    return True, "", ""


# --------------------------------------------------------------------------
# Hugging Face metadata probe (no download)
# --------------------------------------------------------------------------


def probe_hf(dataset_id: str, cache: dict[str, Any]) -> dict[str, Any]:
    """Ask the Hub for a dataset's gated flag and repository size in bytes.

    The size is the whole repository, which over-counts: an eval usually loads a
    single split. It is used only as a conservative upper bound for the disk cap,
    and the file records it as such.
    """
    if dataset_id in cache:
        return cache[dataset_id]
    import urllib.error
    import urllib.request

    record: dict[str, Any] = {"dataset": dataset_id, "gated": None, "bytes": None, "error": None}
    try:
        with urllib.request.urlopen(
            f"https://huggingface.co/api/datasets/{dataset_id}", timeout=30
        ) as resp:
            meta = json.loads(resp.read().decode("utf-8"))
        gated = meta.get("gated")
        record["gated"] = bool(gated) if gated is not None else None
        with urllib.request.urlopen(
            f"https://huggingface.co/api/datasets/{dataset_id}/tree/main?recursive=true",
            timeout=60,
        ) as resp:
            tree = json.loads(resp.read().decode("utf-8"))
        record["bytes"] = sum(int(f.get("size") or 0) for f in tree if isinstance(f, dict))
    except urllib.error.HTTPError as exc:
        record["error"] = f"HTTP {exc.code}"
        if exc.code in (401, 403):
            record["gated"] = True
    except Exception as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"[:200]
    cache[dataset_id] = record
    return record


# --------------------------------------------------------------------------
# The inventory
# --------------------------------------------------------------------------


def discover(probe: bool = False, cache_path: pathlib.Path | None = None) -> list[TaskInfo]:
    root = package_root()
    registered = registered_task_names()

    cache: dict[str, Any] = {}
    if cache_path and cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))

    tasks: list[TaskInfo] = []
    for yaml_path in sorted(root.glob("*/eval.yaml")):
        directory = yaml_path.parent
        try:
            meta = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
        except Exception:
            meta = {}
        source = parse_eval_dir(directory)

        asset_types = [
            a.get("type", "") for a in (meta.get("external_assets") or []) if isinstance(a, dict)
        ]
        hf_datasets = [
            a.get("source", "")
            for a in (meta.get("external_assets") or [])
            if isinstance(a, dict) and a.get("type") == "huggingface"
        ]
        has_sandbox_files = bool(
            list(directory.rglob("compose.y*ml"))
            or list(directory.rglob("docker-compose.y*ml"))
            or list(directory.rglob("Dockerfile"))
        )

        for entry in meta.get("tasks") or []:
            if not isinstance(entry, dict):
                continue
            func_name = entry.get("name", "")
            expr = source.task_scorers.get(func_name) or source.resolve_scorer(func_name)
            try:
                bases = _call_base_names(ast.parse(expr, mode="eval").body) if expr else []
            except SyntaxError:
                bases = []
            scorer_class, scorer_detail = classify_scorer(bases, source)

            info = TaskInfo(
                name=f"inspect_evals/{func_name}",
                eval_id=directory.name,
                title=str(meta.get("title", "")),
                group=str(meta.get("group", "")),
                eval_version=str(meta.get("version", "")),
                dataset_samples=entry.get("dataset_samples"),
                registered=f"inspect_evals/{func_name}" in registered,
                scorer_expr=expr,
                scorer_bases=bases,
                scorer_class=scorer_class,
                scorer_detail=scorer_detail,
                asset_types=asset_types,
                hf_datasets=hf_datasets,
                has_sandbox_files=has_sandbox_files,
                declares_sandbox=source.task_sandbox.get(func_name, False)
                or source.resolve_sandbox(func_name),
                isolated=bool(meta.get("isolated")),
                dependency=meta.get("dependency") or meta.get("dependency-group"),
                tags=list(meta.get("tags") or []),
            )

            info.reachable, info.exclusion_reason, info.exclusion_detail = decide_reachability(info)

            # Only probe the Hub for tasks that are otherwise reachable: a task
            # already excluded for a sandbox does not need a size lookup.
            if probe and info.reachable and hf_datasets:
                for ds in hf_datasets:
                    if not ds:
                        continue
                    record = probe_hf(ds, cache)
                    if record.get("gated"):
                        info.hf_gated = True
                    elif info.hf_gated is None:
                        info.hf_gated = False
                    if record.get("bytes"):
                        info.hf_bytes = max(info.hf_bytes or 0, int(record["bytes"]))
                info.reachable, info.exclusion_reason, info.exclusion_detail = (
                    decide_reachability(info)
                )
            tasks.append(info)

    if cache_path and cache:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")

    tasks.sort(key=lambda t: t.name)
    return tasks


#: How many tasks the first sweep covers. Preregistered.
FIRST_SWEEP_SIZE = 20

#: At most this many tasks from any one eval directory in the first sweep.
#: Without it, near-duplicate variants (``sec_qa`` v1/v2 x 0-shot/5-shot,
#: ``wmdp`` x 3, ``mmlu`` 0/5-shot) would take a third of the slots and the
#: twenty rows would be far more correlated than they look. The week-2 sweep has
#: no such cap; it covers everything reachable.
MAX_TASKS_PER_EVAL = 2


def first_sweep_tasks(
    tasks: Iterable[TaskInfo], size: int = FIRST_SWEEP_SIZE
) -> list[TaskInfo]:
    """The preregistered first-sweep selection, computed rather than typed.

    Rule, fixed in PREREGISTRATION.md before any sweep result exists:

    1. Start from the reachable tasks whose scorer is one of the simple
       deterministic Inspect builtins.
    2. Rank by dataset sample count ascending, ties broken by task name, so the
       first sweep is cheap to run twice for the determinism control.
    3. Take them in that order, skipping a task once its eval directory already
       has ``MAX_TASKS_PER_EVAL`` entries.
    4. Stop at ``size``.

    Anything that turns out to be unreachable when it is actually run is
    replaced by the next task the same rule would have chosen, and the
    substitution is recorded in ``results/coverage.md``.
    """
    per_eval: dict[str, int] = {}
    chosen: list[TaskInfo] = []
    for t in simplest_deterministic(tasks):
        if per_eval.get(t.eval_id, 0) >= MAX_TASKS_PER_EVAL:
            continue
        per_eval[t.eval_id] = per_eval.get(t.eval_id, 0) + 1
        chosen.append(t)
        if len(chosen) >= size:
            break
    return chosen


def first_sweep_reserves(
    tasks: Iterable[TaskInfo], size: int = FIRST_SWEEP_SIZE, count: int = 5
) -> list[TaskInfo]:
    """The next tasks the same rule would pick, used to replace failures."""
    extended = first_sweep_tasks(tasks, size=size + count)
    return extended[size:]


def simplest_deterministic(tasks: Iterable[TaskInfo]) -> list[TaskInfo]:
    """Reachable tasks whose scorer is one of the simple deterministic builtins.

    Ordered by the sweep's preference: smallest dataset first, because the first
    sweep should be cheap to repeat, then by name for a stable tie-break.
    """
    out = [
        t
        for t in tasks
        if t.reachable
        and t.scorer_class == "deterministic"
        and set(t.scorer_bases) & SIMPLE_DETERMINISTIC
    ]
    out.sort(key=lambda t: (t.dataset_samples or 10**9, t.name))
    return out


# --------------------------------------------------------------------------
# Generated output
# --------------------------------------------------------------------------


def _esc(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def render_inventory(tasks: list[TaskInfo]) -> str:
    from collections import Counter

    from . import installed_pins

    pins = installed_pins()
    by_class = Counter(t.scorer_class for t in tasks)
    by_reason = Counter(t.exclusion_reason for t in tasks if not t.reachable)
    reachable = [t for t in tasks if t.reachable]

    lines: list[str] = []
    lines.append("# Task inventory")
    lines.append("")
    lines.append(
        "<!-- GENERATED FILE. Do not edit by hand. Regenerate with `evalfloor inventory`. -->"
    )
    lines.append("")
    lines.append(
        f"Built by static analysis of the installed `inspect_evals` "
        f"{pins.get('inspect_evals')} package against `inspect_ai` {pins.get('inspect_ai')}. "
        "No dataset was downloaded to produce this file."
    )
    lines.append("")
    lines.append("## Totals")
    lines.append("")
    lines.append("| | count |")
    lines.append("|---|---|")
    lines.append(f"| tasks declared in `eval.yaml` files | {len(tasks)} |")
    lines.append(f"| of those, registered in `_registry.py` | {sum(1 for t in tasks if t.registered)} |")
    lines.append(f"| reachable for the deterministic sweep | {len(reachable)} |")
    lines.append(f"| excluded | {len(tasks) - len(reachable)} |")
    lines.append("")
    lines.append("## Scorer class")
    lines.append("")
    lines.append("| class | tasks |")
    lines.append("|---|---|")
    for cls, count in sorted(by_class.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"| `{cls}` | {count} |")
    lines.append("")
    lines.append("## Exclusion reasons")
    lines.append("")
    lines.append("| reason | tasks |")
    lines.append("|---|---|")
    for reason, count in sorted(by_reason.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"| `{reason}` | {count} |")
    lines.append("")
    lines.append("## Reachable tasks with simple deterministic scorers")
    lines.append("")
    lines.append("| task | scorer | samples | hub size | group |")
    lines.append("|---|---|---|---|---|")
    for t in simplest_deterministic(tasks):
        size = f"{t.hf_bytes / 1024**2:.1f} MiB" if t.hf_bytes else "-"
        lines.append(
            f"| `{t.name}` | `{_esc(t.scorer_expr)}` | "
            f"{t.dataset_samples if t.dataset_samples is not None else '?'} | {size} | "
            f"{_esc(t.group)} |"
        )
    lines.append("")
    lines.append(f"## First sweep: the preregistered {FIRST_SWEEP_SIZE}")
    lines.append("")
    lines.append(
        f"Selection rule: simple deterministic scorer, reachable, ranked by dataset size "
        f"ascending with ties broken by name, at most {MAX_TASKS_PER_EVAL} tasks per eval "
        f"directory, first {FIRST_SWEEP_SIZE}. Generated, not typed."
    )
    lines.append("")
    lines.append("| # | task | scorer | samples | hub size |")
    lines.append("|---|---|---|---|---|")
    for i, t in enumerate(first_sweep_tasks(tasks), start=1):
        size = f"{t.hf_bytes / 1024**2:.1f} MiB" if t.hf_bytes else "-"
        lines.append(
            f"| {i} | `{t.name}` | `{_esc(t.scorer_expr)}` | {t.dataset_samples} | {size} |"
        )
    lines.append("")
    reserves = first_sweep_reserves(tasks)
    if reserves:
        lines.append(
            "Reserves, in order, replacing any of the twenty that fails at run time: "
            + ", ".join(f"`{t.name}`" for t in reserves)
            + "."
        )
        lines.append("")
    lines.append("## Every task")
    lines.append("")
    lines.append("| task | scorer expression | class | samples | reachable | reason |")
    lines.append("|---|---|---|---|---|---|")
    for t in tasks:
        samples = t.dataset_samples if t.dataset_samples is not None else "?"
        mark = "yes" if t.reachable else "no"
        lines.append(
            f"| `{t.name}` | `{_esc(t.scorer_expr) or '-'}` | `{t.scorer_class}` | "
            f"{samples} | {mark} | {_esc(t.exclusion_reason)} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_inventory(tasks: list[TaskInfo], path: pathlib.Path) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_inventory(tasks), encoding="utf-8")
    return path


def write_inventory_json(tasks: list[TaskInfo], path: pathlib.Path) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([t.to_dict() for t in tasks], indent=2, sort_keys=True), encoding="utf-8"
    )
    return path
