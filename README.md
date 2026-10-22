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

🔒 Security Note: the script only reads the clock and writes to stdout or the
file you name with `--export`. If you later turn the CSV into real commits,
use a dedicated throwaway repository and a non-privileged token, and keep in
mind that backdated commits are visible in git history and can be spotted.
