# Test entry points. The harness runs in WSL (docs/development.md), so each
# target calls into WSL and is meant to be run from Windows (Git Bash).
# Inside WSL, run the suite directly: cd harness && uv run pytest
#
#   make test-pytest                         run the harness tests
#   make test-pytest JUNIT=<file>            also write a JUnit XML report
#   make test-pytest PYTEST_ARGS="-k leak"   pass extra arguments to pytest

WSL_BASH := wsl.exe -d Ubuntu --exec bash -lc

.PHONY: test-pytest
test-pytest:
	$(WSL_BASH) 'cd "$$(wslpath -u "$(CURDIR)")/harness" && uv run --frozen pytest $(if $(JUNIT),--junitxml="$$(wslpath -u "$(abspath $(JUNIT))")") $(PYTEST_ARGS)'
