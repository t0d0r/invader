# invader - GitHub contribution grid art
#
# Targets:
#   make            show this help
#   make run        animate the grid in the terminal
#   make static     print the finished grid only
#   make export     write plan.csv with date,level,commits for every day
#   make commit     top up backdated empty commits in this repo up to today
#   make push       push main to origin
#   make update     commit + push (what the daily workflow runs)
#   make check      byte-compile the script
#   make clean      remove generated files

PYTHON ?= python3
REPO   ?= .
PLAN   ?= plan.csv
THEME  ?= dark
DELAY  ?= 0.03

.PHONY: help run static export commit push update check clean

help:
	@sed -n 's/^#   //p' $(MAKEFILE_LIST)

run:
	$(PYTHON) invader.py --theme $(THEME) --delay $(DELAY)

static:
	$(PYTHON) invader.py --no-anim --theme $(THEME)

export:
	$(PYTHON) invader.py --no-anim --export $(PLAN) >/dev/null

commit:
	$(PYTHON) invader.py --commit $(REPO)

push:
	git -C $(REPO) push origin main

update: commit push

check:
	$(PYTHON) -m py_compile invader.py

clean:
	rm -rf __pycache__ $(PLAN)
