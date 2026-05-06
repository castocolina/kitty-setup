# kitty-setup — thin glue. Each target is at most five lines including its banner.
# Anything longer dispatches into tools/ or a [project.scripts] entry point.
# See docs/agent-iteration.md (R3 — Makefile is thin).

.DEFAULT_GOAL := help
.PHONY: help install setup clean doctor test uninstall prune

help:
	@echo "kitty-setup targets:"
	@echo "  install                  provision uv → uv tool install → kitty + config (tools/setup.sh)"
	@echo "  setup                    alias of 'install'"
	@echo "  clean                    strip our config block + wipe ./tmp/ scratch (keeps kitty + binary)"
	@echo "  doctor                   diagnose install state and config-include health"
	@echo "  test                     run pytest (set KITTI_INTEGRATION=1 for integration tests)"
	@echo "  uninstall                remove EVERYTHING we created (tools/uninstall.sh)"
	@echo "  uninstall KEEP_BACKUPS=1 preserve kitty.conf.bak.* files; remove the rest"
	@echo "  uninstall KEEP_CONFIG=1  preserve entire ~/.config/kitty/ footprint; remove kitty.app"
	@echo "  uninstall KEEP_KITTY=1   preserve kitty.app + symlink + desktop; remove config + backups"
	@echo "  prune                    keep 3 most recent kitty.conf backups, delete the rest"

install: setup

setup:
	@./tools/setup.sh

clean:
	@my-kitty uninstall || true
	@rm -rf tmp/

doctor:
	@my-kitty doctor

test:
	@uv run pytest tests/

uninstall:
	@KEEP_BACKUPS="$(KEEP_BACKUPS)" KEEP_CONFIG="$(KEEP_CONFIG)" KEEP_KITTY="$(KEEP_KITTY)" ./tools/uninstall.sh

prune:
	@my-kitty prune --backups --keep 3
