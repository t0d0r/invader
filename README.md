# invader

Terminal simulation of a GitHub contribution grid being filled one day at a
time, with a Space Invaders formation tiled across the year. No dependencies beyond
Python 3.10+ and a truecolor-capable terminal.

```bash
python3 invader.py                   # animate (dark theme, 30 ms per day)
python3 invader.py --theme light --delay 0.01
python3 invader.py --no-anim         # print the finished grid only
python3 invader.py --export plan.csv # date,level,commits for every day
python3 invader.py --end 2027-01-31  # simulate a grid ending on another date
python3 invader.py --commit .        # top up backdated empty commits in a repo
make                                 # list Makefile targets
```

## How it works

- The grid is 53 week columns by 7 day rows (Sun..Sat), the last column
  ending on `--end` (default today), exactly like GitHub.
- `FRAMES` in `invader.py` holds the Space Invaders crab from bstconsult.com
  (arms down, arms up), each frame 7 rows by 11 columns. The original sprite
  is 8 rows tall, so the top antenna row is dropped to fit the grid. Characters map to levels: `.`=0, `-`=1, `+`=2, `#`=3, `O`=4.
  Frames are tiled left to right with a one-week gap (`FRAME_WIDTH`,
  `FRAME_GAP`), so edit them to change the figure.
- Each simulated day looks up its cell in the tiled pattern and lights it with
  the GitHub palette for that level. The highlighted cell is the day currently
  being filled.
- `--export` writes a CSV with an approximate commit count per day
  (`COMMITS_PER_LEVEL`). GitHub assigns levels by quartiles of your real
  activity, so the exact counts needed may differ.
- The pattern is anchored to `PATTERN_EPOCH` (a Sunday), not to the grid
  start, so every calendar date has a fixed cell forever. Invaders march one
  column to the left each week and new ones appear on the right.
- `--commit REPO` creates that many empty commits per day in `REPO`, with the
  author and committer dates set to the simulated day and generated
  Conventional Commit subjects. Each commit body records the grid cell it
  fills. Re-running only adds days after the newest planted commit, so it is
  safe to call daily. Push the branch and, for a private repo, enable
  "Include private contributions" in your GitHub profile settings.

## Keeping it going

`make update` runs `--commit .` and pushes `main`. The workflow in
`.github/workflows/invader.yml` does that every day at 10:00 UTC, authoring
commits with the configured name and email so they count on the profile.
Trigger it by hand from the Actions tab with "Run workflow".

GitHub counts at most about 1000 commits per push, so if you ever plant a
long stretch at once, push it in batches.

🔒 Security Note: without `--commit` the script only reads the clock and writes
to stdout or the file you name with `--export`. `--commit` runs `git commit`
in the repository you point it at and refuses to run with staged changes, but
still use it only in a dedicated throwaway repository with a non-privileged
token. Backdated commits are visible in git history and can be spotted.
