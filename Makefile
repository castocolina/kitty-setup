# kitty-setup — thin glue. Each target is at most five lines including its banner.
# Anything longer dispatches into tools/ or a [project.scripts] entry point.
# See docs/agent-iteration.md (R3 — Makefile is thin).

.DEFAULT_GOAL := help
.PHONY: help install setup clean doctor test uninstall

help:
	@echo "kitty-setup targets:"
	@echo "  install    install kitty + inject our config (alias of 'setup')"
	@echo "  setup      install kitty + inject our config (calls tools/setup.sh)"
	@echo "  clean      strip our config block + wipe ./tmp/ scratch (keeps kitty)"
	@echo "  doctor     diagnose install state and config-include health"
	@echo "  test       run pytest (set KITTI_INTEGRATION=1 for integration tests)"
	@echo "  uninstall  remove kitty + strip config (calls tools/uninstall.sh)"

install: setup

setup:
	@./tools/setup.sh

clean:
	@uv run kitty-setup-install --uninstall-config
	@rm -rf tmp/

doctor:
	@uv run kitty-setup-doctor

test:
	@uv run pytest tests/

uninstall:
	@./tools/uninstall.sh
