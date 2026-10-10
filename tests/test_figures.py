"""The README figures: their rows equal the payload, their files carry one digest.

The data and digest tests run without matplotlib. The drawing tests skip without
it, and the GIF tests skip without Pillow. Nothing here touches the network.
"""

from __future__ import annotations

import copy
import json
import pathlib
import re
import subprocess
import sys
from collections import Counter

import pytest

from evalfloor import closeout, figures
from evalfloor.report import floors_from_payload
from evalfloor.rulings import apply_rulings, load_rulings

ROOT = pathlib.Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
FIG_DIR = ROOT / "docs" / "figures"


# --------------------------------------------------------------------------
# Inputs, read the way report reads them
# --------------------------------------------------------------------------


def _json(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _anchor_payload() -> dict:
    try:
        return json.loads(figures.git_show(closeout.LIST_FIXED_AT, "results/sweep.json", cwd=ROOT))
    except (OSError, subprocess.CalledProcessError) as exc:  # pragma: no cover - no git
        pytest.skip(f"git cannot read the anchor payload: {exc}")


@pytest.fixture(scope="module")
def committed():
    payload = _json(RESULTS / "sweep.json")
    rules = load_rulings(ROOT / "rulings.jsonl")
    after, _, _ = apply_rulings(floors_from_payload(payload), rules)
    anchor_inventory = _json(RESULTS / "graded" / "task_inventory.json")
    release_inventory = _json(RESULTS / "task_inventory.json")
    counts = closeout.counts(after, payload, rules, release_inventory, anchor_inventory)
    try:
        anchor = json.loads(figures.git_show(closeout.LIST_FIXED_AT, "results/sweep.json", cwd=ROOT))
    except (OSError, subprocess.CalledProcessError):  # pragma: no cover - no git
        anchor = None
    data = figures.figure_data(
        after, payload, counts, anchor,
        {"anchor": anchor_inventory, "release": release_inventory}, rulings=rules,
    )
    return {
        "payload": payload, "rules": rules, "after": after, "counts": counts, "data": data,
        "anchor_inventory": anchor_inventory, "release_inventory": release_inventory,
    }


def _fixture_after(anchor: dict, release: str = "0.24.0", majority: float | None = None) -> dict:
    """A FIXTURE close-out payload: the anchor with paws as the fix leaves it.
    Not a measurement; only the shape a 0.24.0 payload will have."""
    after = copy.deepcopy(anchor)
    after["pins"]["inspect_evals"] = release
    for row in after["floors"]:
        if row["task"] == figures.FIX_TASK:
            row["scorer"] = "inspect_ai/pattern"
            for name in ("all_labels", "echo"):
                row["members"][name].update(mean=0.0, n_correct=0)
            row["members"]["format_only"]["example_completion"] = "ANSWER: B"
            row["flagged"], row["flagged_by"] = False, []
            if majority is not None:
                row["majority"] = majority
                row["members"]["majority"]["mean"] = majority
    return after


def _numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)*", text))


# --------------------------------------------------------------------------
# F1: rows equal the payload
# --------------------------------------------------------------------------


def test_f1_rows_equal_the_payload(committed) -> None:
    rows, counts, after = committed["data"]["F1"], committed["counts"], committed["after"]
    by_task: dict[str, list] = {}
    for f in after:
        by_task.setdefault(f.task, []).append(f)

    drawn = [r for r in rows if r["state"] != "not_run"]
    assert {r["task"] for r in drawn if r["state"] in ("flag", "tie")} == set(counts.flagged)
    assert {r["task"] for r in drawn if r["state"] in ("flag", "tie")} == {
        t for t, fs in by_task.items() if t in counts.ran and closeout.representative_floor(fs).flagged
    }
    assert {r["task"] for r in drawn if r["state"] == "tie"} == {
        t for t, fs in by_task.items() if t in counts.ran and closeout.representative_floor(fs).collision
    } == set(counts.ties)
    assert {r["task"] for r in drawn} == set(counts.ran)
    assert {(r["task"], r["reason"]) for r in rows if r["state"] == "not_run"} == set(counts.not_run)
    for r in drawn:
        f = closeout.representative_floor(by_task[r["task"]])
        assert (r["scorer"], r["majority"], r["best_member"], r["best_mean"], r["gap"]) == (
            f.scorer, f.majority, f.best_member, f.best_mean, f.gap_to_majority
        )
        assert r["flagged_by"] == list(f.flagged_by)
        if r["state"] == "flag":
            # The member the README's first line names.
            assert r["flag_member"] == min(f.flagged_by, key=lambda m: (-f.members[m].mean, m))
            assert r["flag_mean"] == f.members[r["flag_member"]].mean
    gaps = [r["gap"] for r in drawn]
    assert gaps == sorted(gaps, reverse=True)


def test_f1_cause_comes_only_from_a_note_ruling(committed) -> None:
    from evalfloor.rulings import Ruling

    c = committed["counts"]
    if not c.real_flags:
        pytest.skip("no real flag in this payload")
    task = c.real_flags[0]
    base = [r for r in committed["rules"] if not (r.action == "note" and r.task == task)]

    def cause(rules) -> str:
        return next(r for r in figures.f1_rows(committed["after"], c, rules) if r["task"] == task)["cause"]

    note = Ruling(task=task, action="note", reason="A task property: the input ends in the label.",
                  source="x.py:1")
    vague = Ruling(task=task, action="note", reason="Read the scorer.", source="x.py:2")
    assert cause(base) == ""
    assert cause(base + [note]) == "task property"
    assert cause(base + [note, vague]) == ""  # the last note wins, as in the README's line


def test_f1_title_is_computed_from_the_counts(committed) -> None:
    rows, c = committed["data"]["F1"], committed["counts"]
    text = figures.title("F1", rows, c)
    assert text == (
        f"{c.F - c.K} of {c.N} beyond {c.K} {'tie' if c.K == 1 else 'ties'}, inspect_evals {c.release}"
    )
    allowed = {str(c.F - c.K), str(c.N), str(c.K), str(c.F), c.release}
    assert _numbers(text) <= allowed
    # Subtitle numbers too: no number appears that the counts do not give.
    assert _numbers(figures.subtitle("F1", rows, c)) <= allowed | {"4", "8.5"}  # §4, §8.5


def test_f1_title_moves_when_the_payload_does(committed) -> None:
    payload = copy.deepcopy(committed["payload"])
    flagged = set(committed["counts"].flagged)
    # Drop every flagged floor: the title must say 0 beyond 0.
    payload["floors"] = [r for r in payload["floors"] if r["task"] not in flagged]
    payload["tasks"] = [t for t in payload["tasks"] if t not in flagged]
    after = figures.floors_after_rulings(payload, committed["rules"])
    c = closeout.counts(after, payload, committed["rules"], committed["release_inventory"],
                        committed["anchor_inventory"])
    rows = figures.f1_rows(after, c)
    assert figures.title("F1", rows, c).startswith(f"0 of {c.N} beyond 0 ties")
    assert c.N == committed["counts"].N - len(flagged)


def test_f1_csv_round_trips(committed, tmp_path) -> None:
    rows = committed["data"]["F1"]
    path = figures.write_data(rows, tmp_path / "f1.csv", figures.FIELDS["F1"])
    assert b"\r\n" not in path.read_bytes()
    back = figures.read_data(path)
    assert back == [{k: figures.cell(r[k]) for k in figures.FIELDS["F1"]} for r in rows]
    for r, b in zip(rows, back):
        if r["best_mean"] is not None:
            assert float(b["best_mean"]) == r["best_mean"] and float(b["majority"]) == r["majority"]


# --------------------------------------------------------------------------
# F3: one bar over the anchor inventory
# --------------------------------------------------------------------------


def test_f3_partitions_the_anchor_inventory(committed) -> None:
    rows, inv, c = committed["data"]["F3"], committed["anchor_inventory"], committed["counts"]
    assert rows[0]["start"] == 0 and rows[-1]["end"] == len(inv)
    for a, b in zip(rows, rows[1:]):
        assert a["end"] == b["start"]
    tasks = [t for r in rows for t in r["tasks"]]
    assert sorted(tasks) == sorted(str(r["name"]) for r in inv)  # each task once
    assert all(r["count"] == len(r["tasks"]) for r in rows)

    reasons = Counter(r["exclusion_reason"] for r in inv if not r["reachable"])
    excluded = [r for r in rows if r["kind"] == "excluded"]
    assert sum(r["count"] for r in excluded) == sum(reasons.values())
    reachable = {str(r["name"]) for r in inv if r["reachable"]}
    countable = set(figures.default_countable(committed["payload"], committed["rules"]))
    by_kind = {k: {t for r in rows if r["kind"] == k for t in r["tasks"]} for k in ("not_counted", "ran", "not_run")}
    assert by_kind["not_counted"] == reachable - countable
    assert by_kind["ran"] | by_kind["not_run"] == countable
    assert by_kind["ran"] == set(c.ran) & countable
    treatments = {r.task: r.treatment for r in committed["rules"] if r.action == "not_counted"}
    nc = next(r for r in rows if r["kind"] == "not_counted")
    for task in nc["tasks"]:
        if task in treatments:
            assert treatments[task] in nc["detail"]


def test_f3_title_and_caption_are_computed(committed) -> None:
    rows, c = committed["data"]["F3"], committed["counts"]
    t = {k: sum(r["count"] for r in rows if r["kind"] in ks) for k, ks in
         {"countable": ("ran", "not_run"), "ran": ("ran",)}.items()}
    assert figures.title("F3", rows, c) == (
        f"{t['countable']} of {len(committed['anchor_inventory'])} declared tasks are countable; "
        f"{t['ran']} ran on inspect_evals {c.release}"
    )
    cap = figures.caption("F3", rows, c)
    if c.release == c.anchor_release:
        assert "own inventory" not in cap  # the release inventory is caption-only, and only after a bump
    else:
        assert f"reaches {c.R} of {c.D}" in cap


# --------------------------------------------------------------------------
# F2 and G1: the anchor against a fixture
# --------------------------------------------------------------------------


def test_f2_rows_read_each_release_from_its_own_payload() -> None:
    anchor = _anchor_payload()
    after = _fixture_after(anchor, majority=0.6)
    rows = figures.f2_rows(anchor, after)
    paws_b = next(f for f in floors_from_payload(anchor) if f.task == figures.FIX_TASK)
    paws_a = next(f for f in floors_from_payload(after) if f.task == figures.FIX_TASK)
    assert [r["member"] for r in rows] == [m for m in figures.CONTENT_FREE_NAMES if m in paws_b.members]
    for r in rows:
        mb, ma = paws_b.members[r["member"]], paws_a.members[r["member"]]
        assert (r["score_before"], r["score_after"]) == (mb.mean, ma.mean)
        assert (r["completion_before"], r["completion_after"]) == (mb.example_completion, ma.example_completion)
        assert r["reaches_before"] == (r["member"] in paws_b.flagged_by)
        assert r["reaches_after"] == (r["member"] in paws_a.flagged_by)
        assert (r["majority_before"], r["majority_after"]) == (paws_b.majority, 0.6)
    assert figures.title("F2", rows) == "paws: all_labels reaches the majority on 0.20.0; none does on 0.24.0"
    # Two majorities, two named values; a changed completion shows both.
    assert "55.8% on 0.20.0, 60.0% on 0.24.0" in figures.subtitle("F2", rows, None)
    assert '"ANSWER: A" / "ANSWER: B"' in figures.table_twin("F2", rows)


def test_figure_data_has_no_f2_on_the_anchor_release(committed) -> None:
    anchor = _anchor_payload()
    c = committed["counts"]
    same = figures.figure_data(committed["after"], anchor, c, anchor)
    assert "F2" not in same
    after = _fixture_after(anchor)
    floors = figures.floors_after_rulings(after, committed["rules"])
    c2 = closeout.counts(floors, after, committed["rules"], committed["release_inventory"],
                         committed["anchor_inventory"])
    assert "F2" in figures.figure_data(floors, after, c2, anchor)


def test_g1_timeline_fits_its_running_time() -> None:
    rows = figures.f2_rows(_anchor_payload(), _fixture_after(_anchor_payload()))
    frames = figures.g1_timeline(rows)
    total = sum(ms for *_, ms in frames) / 1000
    lo, hi = figures.G1_SECONDS
    assert lo <= total <= hi
    assert frames[-1][3] is True and frames[-1][4] >= 2500  # the verdict, held
    assert 60 <= len(frames) <= 200


# --------------------------------------------------------------------------
# Digests, text, and the pure API
# --------------------------------------------------------------------------


def test_data_digest_is_over_rows_not_bytes() -> None:
    rows = [{"a": 1, "b": [1.5, "x"]}, {"b": None, "a": 2}]
    same = [{"b": (1.5, "x"), "a": 1}, {"a": 2, "b": None}]
    assert figures.data_digest(rows) == figures.data_digest(same)
    assert figures.data_digest(rows) != figures.data_digest([{"a": 1, "b": [1.5, "y"]}, rows[1]])
    assert re.fullmatch(r"[0-9a-f]{64}", figures.data_digest(rows))


def test_figures_imports_no_drawing_library_at_module_level() -> None:
    import ast

    tree = ast.parse(pathlib.Path(figures.__file__).read_text(encoding="utf-8"))
    top: set[str] = set()
    for node in tree.body:  # module level only; drawing code imports inside functions
        if isinstance(node, ast.Import):
            top |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            top.add(node.module.split(".")[0])
    assert not top & {"matplotlib", "PIL"}


def test_members_above_zero_names_every_scoring_member(committed) -> None:
    after = committed["after"]
    sentence = figures.members_above_zero(after)
    for member, tasks in figures.members_above_zero_rows(after).items():
        expected = {
            f.task for f in after
            if f.error is None and f.members and not f.nothing_scored
            and member in f.members and f.members[member].applicable and f.members[member].mean > 0
        }
        assert set(tasks) == expected
        assert f"`{member}`" in sentence


def test_table_twin_and_alt_text_cover_every_row(committed) -> None:
    c = committed["counts"]
    for fig_id, rows in committed["data"].items():
        table = figures.table_twin(fig_id, rows)
        assert len(table.splitlines()) >= len(rows) + 2
        alt = figures.alt_text(fig_id, rows, c)
        assert c.release in alt
    f1 = committed["data"]["F1"]
    alt = figures.alt_text("F1", f1, c)
    for r in f1:
        if r["state"] in ("flag", "tie"):
            assert figures._short(r["task"]) in alt


# --------------------------------------------------------------------------
# Drawing: every variant written, one digest, 1920x1080, byte-stable
# --------------------------------------------------------------------------


def _png_size(path: pathlib.Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def _png_description(path: pathlib.Path) -> str:
    data, pos = path.read_bytes(), 8
    while pos < len(data):
        n = int.from_bytes(data[pos : pos + 4], "big")
        kind, body = data[pos + 4 : pos + 8], data[pos + 8 : pos + 8 + n]
        if kind == b"tEXt" and body.startswith(b"Description\x00"):
            return body.split(b"\x00", 1)[1].decode("latin-1")
        pos += 12 + n
    return ""


def _check_written(paths: list[pathlib.Path], rows, stem: str) -> None:
    digest = figures.data_digest(rows)
    names = {p.name for p in paths}
    assert names == {f"{stem}.csv"} | {f"{stem}-{m}.{x}" for m in ("light", "dark") for x in ("svg", "png")}
    for p in paths:
        if p.suffix == ".png":
            assert _png_size(p) == figures.SIZE
            assert f"rows sha256 {digest}" in _png_description(p)
        if p.suffix == ".svg":
            text = p.read_text(encoding="utf-8")
            assert f"rows sha256 {digest}" in text
            assert "<text" not in text  # glyphs are paths, so GitHub draws them exactly
            assert "<dc:date>" not in text
            assert 'viewBox="0 0 1382.4 777.6"' in text  # 1920x1080 at 72 dpi


def test_static_figures_write_every_variant_with_one_digest(committed, tmp_path) -> None:
    pytest.importorskip("matplotlib")
    for fig_id in ("F1", "F3"):
        rows = committed["data"][fig_id]
        paths = figures.render_static(fig_id, rows, committed["counts"], tmp_path)
        _check_written(paths, rows, figures.FIGURE_NAMES[fig_id])
        assert figures.read_data(tmp_path / f"{figures.FIGURE_NAMES[fig_id]}.csv") == [
            {k: figures.cell(r[k]) for k in figures.FIELDS[fig_id]} for r in rows
        ]


def test_f2_draws_from_a_fixture(tmp_path) -> None:
    pytest.importorskip("matplotlib")
    anchor = _anchor_payload()
    rows = figures.f2_rows(anchor, _fixture_after(anchor, majority=0.6))
    paths = figures.render_static("F2", rows, None, tmp_path, "FIXTURE")
    _check_written(paths, rows, figures.FIGURE_NAMES["F2"])


def test_svg_and_png_bytes_are_stable(committed, tmp_path) -> None:
    pytest.importorskip("matplotlib")
    rows = committed["data"]["F1"]
    a = figures.render_static("F1", rows, committed["counts"], tmp_path / "a")
    b = figures.render_static("F1", rows, committed["counts"], tmp_path / "b")
    for pa, pb in zip(a, b):
        assert pa.read_bytes() == pb.read_bytes(), pa.name


def test_f1_splits_into_two_panels_past_its_row_cap(committed, tmp_path) -> None:
    pytest.importorskip("matplotlib")
    rows = [r for r in committed["data"]["F1"] if r["state"] != "not_run"]
    many = []
    for k in range(figures.F1_ROWS_PER_PANEL // max(1, len(rows)) + 2):
        many += [dict(r, task=f"{r['task']}_{k}") for r in rows]
    many.append(dict(rows[0], task="inspect_evals/broken", state="not_run", reason="load_error: boom",
                     majority=None, best_mean=None, gap=None))
    paths = figures.render_static("F1", many, committed["counts"], tmp_path)
    assert all(_png_size(p) == figures.SIZE for p in paths if p.suffix == ".png")


# --------------------------------------------------------------------------
# GIFs
# --------------------------------------------------------------------------


def _gif_stats(path: pathlib.Path) -> tuple[tuple[int, int], int, int, int]:
    from PIL import Image

    with Image.open(path) as im:
        total, last = 0, 0
        for k in range(im.n_frames):
            im.seek(k)
            last = im.info.get("duration", 0)
            total += last
        return im.size, im.n_frames, total, last


def test_g1_renders_the_anchor_against_a_fixture(tmp_path) -> None:
    pytest.importorskip("PIL")
    anchor = _anchor_payload()
    rows = figures.f2_rows(anchor, _fixture_after(anchor))
    path = figures.render_g1(rows, tmp_path / "g1.gif", sources=["anchor", "FIXTURE"])
    size, n, total, last = _gif_stats(path)
    assert size == figures.SIZE
    assert path.stat().st_size <= figures.G1_MAX_BYTES
    lo, hi = figures.G1_SECONDS
    assert lo * 1000 <= total <= hi * 1000
    assert last >= 2500
    assert 20 <= n <= 200  # identical neighbours are merged by the encoder


def _fake_capture(release: str = "0.20.0", flagged: bool = True) -> dict:
    lines = [
        (0.8, "stdout", "line", "Loading dataset google-research-datasets/paws from Hugging Face..."),
        (0.9, "stderr", "cr", ""),
        (1.0, "stderr", "cr", "Saving the dataset (0/1 shards):   0%|          | 0/8000"),
        (1.1, "stderr", "line", "Saving the dataset (1/1 shards): 100%|##########| 8000/8000"),
        (9.0, "stdout", "line", f"inspect_evals/paws  (inspect_ai 0.3.263, inspect_evals {release})"),
        (9.0, "stdout", "line", "    all_labels     100.00%  8000/8000  <-- at or above majority"),
        (9.1, "stderr", "line", ""),
        (9.1, "stderr", "line", "inspect_evals/paws: " + ("FLAGGED" if flagged else "clean")),
    ]
    return {
        "command": ["evalfloor", "check", "inspect_evals/paws"],
        "display": "evalfloor check inspect_evals/paws",
        "started_at": "2026-10-10T12:00:00+00:00",
        "elapsed_s": 9.4,
        "returncode": 1 if flagged else 0,
        "events": [{"t": t, "stream": s, "kind": k, "text": x} for t, s, k, x in lines],
    }


def test_g2_renders_fake_capture_text(tmp_path) -> None:
    pytest.importorskip("PIL")
    caps = [_fake_capture(), _fake_capture("0.24.0", flagged=False)]
    text = figures.g2_transcript(caps)
    assert text.count("$ evalfloor check inspect_evals/paws") == 2
    assert "Saving the dataset (0/1 shards)" not in text  # the progress line was redrawn
    assert "Saving the dataset (1/1 shards): 100%" in text
    assert [figures.capture_verdicts(c) for c in caps] == [
        {"inspect_evals/paws": "FLAGGED"}, {"inspect_evals/paws": "clean"}
    ]
    assert [figures.capture_release(c) for c in caps] == ["0.20.0", "0.24.0"]
    frames = figures.g2_timeline(caps)
    assert all(f["ms"] <= 700 for f in frames if not f["exit"] and f["upto"])  # waits compressed
    assert frames[-1]["exit"] and frames[-1]["clock"] == 9.4  # the real time is kept
    path = figures.render_g2(caps, tmp_path / "g2.gif")
    size, _, _, last = _gif_stats(path)
    assert size == figures.SIZE and last >= 3000
    assert path.stat().st_size <= figures.G2_MAX_BYTES


def test_line_splitter_handles_carriage_returns_across_chunks() -> None:
    sp = figures._LineSplitter()
    out = sp.feed("a\r") + sp.feed("\nprogress 1\rprogress 2\r") + sp.feed("\ndone") + sp.close()
    assert out == [("line", "a"), ("cr", "progress 1"), ("line", "progress 2"), ("line", "done")]


def test_capture_records_both_streams_with_times() -> None:
    code = (
        "import sys, time; print('one'); sys.stdout.flush(); time.sleep(0.3); "
        "print('two', file=sys.stderr); sys.exit(3)"
    )
    cap = figures.capture([sys.executable, "-c", code], display="python -c ...")
    assert cap["returncode"] == 3
    texts = [(e["stream"], e["text"]) for e in cap["events"]]
    assert texts == [("stdout", "one"), ("stderr", "two")]
    assert cap["events"][1]["t"] - cap["events"][0]["t"] >= 0.2
    assert figures.transcript(cap) == "$ python -c ...\none\ntwo\n"


def test_the_provider_gives_report_every_readme_figure(committed, tmp_path) -> None:
    """``make_figure_provider`` against report's own FigureRef and render_figure,
    on the anchor and a FIXTURE 0.24.0 payload, with a fake G2 capture."""
    pytest.importorskip("matplotlib")
    from evalfloor.report import README_FIGURES, render_figure

    results = tmp_path / "results"
    (results / "graded").mkdir(parents=True)
    (results / "graded" / "task_inventory.json").write_text(json.dumps(committed["anchor_inventory"]))
    (results / "task_inventory.json").write_text(json.dumps(committed["release_inventory"]))
    out = tmp_path / "docs" / "figures"
    out.mkdir(parents=True)
    (out / "g2-fake.json").write_text(json.dumps(_fake_capture("0.24.0", flagged=False)))

    after = _fixture_after(_anchor_payload())
    floors = figures.floors_after_rulings(after, committed["rules"])
    c = closeout.counts(floors, after, committed["rules"], committed["release_inventory"],
                        committed["anchor_inventory"])
    provider = figures.make_figure_provider(out, results=results, rulings_path=ROOT / "rulings.jsonl",
                                            root=tmp_path)
    refs = provider(payload=after, floors=floors, counts=c, repeat=None)
    assert sorted(r.id for r in refs) == sorted(README_FIGURES)
    for ref in refs:
        for rel in filter(None, (ref.light_svg, ref.dark_svg, ref.gif)):
            assert (tmp_path / rel).exists(), rel
            assert not pathlib.PurePosixPath(rel).is_absolute()
        assert re.fullmatch(r"[0-9a-f]{64}", ref.data_digest)
        assert "\n".join(render_figure(ref))
    g2 = next(r for r in refs if r.id == "G2")
    assert "inspect_evals/paws: clean" in g2.transcript


# --------------------------------------------------------------------------
# The committed files in docs/figures
# --------------------------------------------------------------------------


def _payload_for_release(release: str) -> dict | None:
    current = _json(RESULTS / "sweep.json")
    if (current.get("pins") or {}).get("inspect_evals") == release:
        return current
    anchor = _anchor_payload()
    if (anchor.get("pins") or {}).get("inspect_evals") == release:
        return anchor
    return None


def test_g2_transcripts_agree_with_their_payloads() -> None:
    transcripts = sorted(FIG_DIR.glob("g2-*.txt"))
    if not transcripts:
        pytest.skip("no G2 capture recorded yet")
    rules = load_rulings(ROOT / "rulings.jsonl")
    checked = 0
    for path in transcripts:
        for session in re.split(r"\n(?=\$ )", path.read_text(encoding="utf-8")):
            rel = re.search(r"inspect_evals (\d+(?:\.\d+)+)\)", session)
            verdicts = re.findall(r"^(\S+/\S+): (FLAGGED|clean)$", session, flags=re.M)
            if not rel or not verdicts:
                continue
            payload = _payload_for_release(rel.group(1))
            if payload is None:
                continue
            floors = figures.floors_after_rulings(payload, rules)
            for task, verdict in verdicts:
                mine = [f for f in floors if f.task == task]
                assert mine, f"{path.name}: {task} is not in the {rel.group(1)} payload"
                flagged = closeout.representative_floor(mine).flagged
                assert verdict == ("FLAGGED" if flagged else "clean"), (path.name, task)
                checked += 1
    if not checked:
        pytest.skip("no transcript names a release whose payload is committed")


def test_committed_gifs_keep_their_budgets() -> None:
    gifs = sorted(FIG_DIR.glob("*.gif"))
    if not gifs:
        pytest.skip("no GIF written yet")
    pytest.importorskip("PIL")
    for path in gifs:
        size, *_ = _gif_stats(path)
        assert size == figures.SIZE, path.name
        budget = figures.G1_MAX_BYTES if path.name.startswith("g1-") else figures.G2_MAX_BYTES
        assert path.stat().st_size <= budget, path.name


def test_committed_figures_match_the_committed_results(committed) -> None:
    """Never stale: a committed figure's CSV and its four images carry the rows
    the committed results give today. Rerun `python -m evalfloor.figures` when
    this fails."""
    present = [i for i in figures.FIGURE_IDS if (FIG_DIR / f"{figures.FIGURE_NAMES[i]}.csv").exists()]
    if not present:
        pytest.skip("no figure written yet")
    for fig_id in present:
        stem = figures.FIGURE_NAMES[fig_id]
        assert fig_id in committed["data"], f"{stem}.csv exists but the results give it no rows"
        rows = committed["data"][fig_id]
        digest = figures.data_digest(rows)
        csv_rows = figures.read_data(FIG_DIR / f"{stem}.csv")
        assert csv_rows == [{k: figures.cell(r[k]) for k in figures.FIELDS[fig_id]} for r in rows], (
            f"docs/figures/{stem}.csv is stale: rerun python -m evalfloor.figures"
        )
        for mode in ("light", "dark"):
            for ext in ("svg", "png"):
                path = FIG_DIR / f"{stem}-{mode}.{ext}"
                assert path.exists(), path.name
                if ext == "png":
                    assert _png_size(path) == figures.SIZE
                    assert f"rows sha256 {digest}" in _png_description(path), path.name
                else:
                    assert f"rows sha256 {digest}" in path.read_text(encoding="utf-8"), path.name
