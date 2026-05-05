# kitty-setup — thin glue. Each target is at most five lines including its banner.
# Anything longer dispatches into tools/ or a [project.scripts] entry point.
# See docs/agent-iteration.md (R3 — Makefile is thin).

.DEFAULT_GOAL := help
.PHONY: help install setup clean doctor test uninstall prune

help:
	@echo "kitty-setup targets:"
	@echo "  install         provision uv → uv tool install → kitty + config (calls tools/setup.sh)"
	@echo "  setup           alias of 'install'"
	@echo "  clean           strip our config block + wipe ./tmp/ scratch (keeps kitty + binary)"
	@echo "  doctor          diagnose install state and config-include health"
	@echo "  test            run pytest (set KITTI_INTEGRATION=1 for integration tests)"
	@echo "  uninstall       strip our config + payload (calls tools/uninstall.sh)"
	@echo "  uninstall ALL=1 also removes kitty + prints my-kitty-setup self-removal command"
	@echo "  prune           keep 3 most recent kitty.conf backups, delete the rest"

install: setup

setup:
	@./tools/setup.sh

clean:
	@my-kitty-setup uninstall || true
	@rm -rf tmp/

doctor:
	@my-kitty-setup doctor

test:
	@uv run pytest tests/

UNINSTALL_FLAGS := $(if $(filter 1,$(ALL)),--kitty --self,)

uninstall:
	@UNINSTALL_FLAGS="$(UNINSTALL_FLAGS)" ./tools/uninstall.sh

prune:
	@my-kitty-setup prune --backups --keep 3
