#!/usr/bin/env python3
"""invader - simulate a GitHub contribution grid being filled, one day at a
time, with a Space Invaders formation tiled across the year.

The grid matches GitHub's layout: 53 week columns, 7 day rows (Sun..Sat),
the last column ending on `--end` (default: today).

Usage:
  python3 invader.py                 # animate in the terminal
  python3 invader.py --delay 0.01    # faster
  python3 invader.py --no-anim       # just print the finished grid
  python3 invader.py --export plan.csv   # date,level,commits for each day
  python3 invader.py --commit .          # plant backdated empty commits in a repo
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import random
import shutil
import subprocess
import sys
import time

WEEKS = 53
DAYS = 7
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
ROW_LABELS = {1: "Mon", 3: "Wed", 5: "Fri"}

# GitHub palettes, index = contribution level 0..4
THEMES = {
    "light": ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"],
    "dark":  ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"],
}
# Approximate commits per day needed to land in each level.
COMMITS_PER_LEVEL = {0: 0, 1: 1, 2: 3, 3: 6, 4: 10}

# Space Invaders crab, taken from the invader sprite on bstconsult.com.
# The original is 11 x 8 cells; the grid has 7 rows, so the top row with the
# antenna tips is dropped. Two classic animation frames alternate.
# Characters map to levels: '.'=0  '-'=1  '+'=2  '#'=3  'O'=4
CHAR_LEVEL = {".": 0, "-": 1, "+": 2, "#": 3, "O": 4}
FRAMES = [
    [   # arms down
        "...#...#...",
        "..#######..",
        ".##.###.##.",
        "###########",
        "#.#######.#",
        "#.#.....#.#",
        "...##.##...",
    ],
    [   # arms up
        "#..#...#..#",
        "#.#######.#",
        "###.###.###",
        "###########",
        ".#########.",
        "..#.....#..",
        ".#.......#.",
    ],
]
FRAME_WIDTH = 11  # weeks per frame
FRAME_GAP = 1    # empty weeks between frames

# Vocabulary for generated commit subjects (Conventional Commits style).
COMMIT_TYPES = ["feat", "fix", "refactor", "docs", "test", "chore", "perf", "style"]
COMMIT_SCOPES = ["grid", "render", "cli", "pattern", "export", "theme", "frames", "dates"]
COMMIT_VERBS = ["tweak", "adjust", "clean up", "simplify", "update", "polish",
                "rework", "tidy", "improve", "align", "trim", "extend"]
COMMIT_OBJECTS = ["month header", "palette lookup", "frame tiling", "row labels",
                  "cursor highlight", "csv writer", "argument parsing", "legend",
                  "week math", "cell sizing", "docstring", "type hints"]


def rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def paint(text: str, hex_color: str, reverse: bool = False) -> str:
    r, g, b = rgb(hex_color)
    prefix = "\x1b[7m" if reverse else ""
    return f"{prefix}\x1b[38;2;{r};{g};{b}m{text}\x1b[0m"


def build_pattern(frames: list[list[str]], gap: int) -> dict[tuple[int, int], int]:
    """Tile frames left to right; return {(week, day): level}."""
    pattern: dict[tuple[int, int], int] = {}
    col, i = 0, 0
    while col < WEEKS:
        frame = frames[i % len(frames)]
        for day, row in enumerate(frame):
            for c, ch in enumerate(row):
                level = CHAR_LEVEL[ch]
                if level and col + c < WEEKS:
                    pattern[(col + c, day)] = level
        col += FRAME_WIDTH + gap
        i += 1
    return pattern


def day_row(d: dt.date) -> int:
    """0 = Sunday ... 6 = Saturday (GitHub row order)."""
    return (d.weekday() + 1) % 7


def grid_dates(end: dt.date) -> tuple[dt.date, int]:
    """Return (first Sunday of the grid, total number of days up to `end`)."""
    start = end - dt.timedelta(days=(WEEKS - 1) * 7 + day_row(end))
    return start, (end - start).days + 1


def month_header(start: dt.date, cell_w: int) -> str:
    out = [" "] * (WEEKS * cell_w)
    last_end = -1
    prev_month = None
    for week in range(WEEKS):
        sunday = start + dt.timedelta(weeks=week)
        if sunday.month != prev_month:
            pos = week * cell_w
            label = MONTHS[sunday.month - 1]
            if pos > last_end and pos + len(label) <= len(out):
                out[pos:pos + len(label)] = label
                last_end = pos + len(label)
            prev_month = sunday.month
    return "".join(out).rstrip()


def render(filled: dict[tuple[int, int], int], start: dt.date, palette: list[str],
           cursor: tuple[int, int] | None, cell: str, title: str) -> str:
    cell_w = len(cell)
    lines = [title, "", "    " + month_header(start, cell_w)]
    for day in range(DAYS):
        row = [f"{ROW_LABELS.get(day, ''):<4}"]
        for week in range(WEEKS):
            level = filled.get((week, day))
            if level is None:
                row.append(" " * cell_w)        # not yet reached
                continue
            row.append(paint(cell, palette[level], reverse=(week, day) == cursor))
        lines.append("".join(row))
    legend = "Less " + " ".join(paint(cell, c) for c in palette) + " More"
    lines += ["", legend]
    return "\n".join(lines)


def commit_message(rng: random.Random, date: dt.date, level: int, n: int, of: int) -> str:
    subject = (f"{rng.choice(COMMIT_TYPES)}({rng.choice(COMMIT_SCOPES)}): "
               f"{rng.choice(COMMIT_VERBS)} {rng.choice(COMMIT_OBJECTS)}")
    body = f"Contribution grid cell {date.isoformat()} level {level}, commit {n}/{of}."
    return f"{subject}\n\n{body}"


def plant_commits(schedule: list[tuple[dt.date, int]], repo: str) -> int:
    """Create backdated empty commits in `repo`, COMMITS_PER_LEVEL per day."""
    git = ["git", "-C", repo]
    subprocess.run(git + ["rev-parse", "--is-inside-work-tree"], check=True,
                   stdout=subprocess.DEVNULL)
    if subprocess.run(git + ["diff", "--cached", "--quiet"]).returncode:
        sys.exit("error: index has staged changes; commit or unstage them first")
    rng = random.Random(0)
    tz = dt.datetime.now().astimezone().tzinfo
    made = 0
    for date, level in schedule:
        count = COMMITS_PER_LEVEL[level]
        for n in range(count):
            when = dt.datetime.combine(date, dt.time(12, 0), tz) + dt.timedelta(minutes=7 * n)
            stamp = when.isoformat()
            env = {**os.environ, "GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp}
            subprocess.run(git + ["commit", "-q", "--allow-empty", "-m",
                                  commit_message(rng, date, level, n + 1, count)],
                           env=env, check=True)
            made += 1
    print(f"created {made} commits in {repo}", file=sys.stderr)
    return made


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--end", type=dt.date.fromisoformat, default=dt.date.today(),
                    help="last day of the grid (YYYY-MM-DD, default today)")
    ap.add_argument("--delay", type=float, default=0.03, help="seconds per day")
    ap.add_argument("--theme", choices=THEMES, default="dark")
    ap.add_argument("--no-anim", action="store_true", help="print final grid only")
    ap.add_argument("--export", metavar="FILE", help="write date,level,commits CSV")
    ap.add_argument("--commit", metavar="REPO",
                    help="create backdated empty commits in REPO instead of animating")
    args = ap.parse_args()

    palette = THEMES[args.theme]
    pattern = build_pattern(FRAMES, FRAME_GAP)
    start, total_days = grid_dates(args.end)
    cols = shutil.get_terminal_size((80, 24)).columns
    cell = "██" if cols >= 4 + WEEKS * 2 else "■"

    schedule = []
    for i in range(total_days):
        date = start + dt.timedelta(days=i)
        level = pattern.get((i // 7, day_row(date)), 0)
        schedule.append((date, level))
    contributions = sum(COMMITS_PER_LEVEL[lvl] for _, lvl in schedule)

    if args.export:
        with open(args.export, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["date", "level", "commits"])
            for date, level in schedule:
                w.writerow([date.isoformat(), level, COMMITS_PER_LEVEL[level]])
        print(f"wrote {len(schedule)} days to {args.export}", file=sys.stderr)

    if args.commit:
        plant_commits(schedule, args.commit)
        return 0

    filled: dict[tuple[int, int], int] = {}
    hide, show, home, clear = "\x1b[?25l", "\x1b[?25h", "\x1b[H", "\x1b[2J"
    try:
        if not args.no_anim:
            sys.stdout.write(hide + clear)
        for i, (date, level) in enumerate(schedule):
            pos = (i // 7, day_row(date))
            filled[pos] = level
            if args.no_anim:
                continue
            done = sum(COMMITS_PER_LEVEL[l] for _, l in schedule[:i + 1])
            title = f"{done} contributions so far   {date:%a %Y-%m-%d}"
            sys.stdout.write(home + render(filled, start, palette, pos, cell, title) + "\n")
            sys.stdout.flush()
            time.sleep(args.delay)
        title = f"{contributions} contributions in the last year"
        sys.stdout.write((home if not args.no_anim else "")
                         + render(filled, start, palette, None, cell, title) + "\n")
    except KeyboardInterrupt:
        pass
    finally:
        if not args.no_anim:
            sys.stdout.write(show)
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
