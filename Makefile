.PHONY: all build clean lint format check test flash venv

# Python virtual environment directory
VENV := .venv
PYTHON := $(VENV)/bin/python3
PIP := $(VENV)/bin/pip

# Default target
all: check build

# Create and setup virtual environment
$(VENV)/bin/activate:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install cppcheck cpplint pytest pytest-cov black pylint platformio

venv: $(VENV)/bin/activate

# Build firmware
build: venv
	$(VENV)/bin/pio run

# Clean build files
clean:
	$(VENV)/bin/pio run -t clean
	rm -rf .pio
	rm -rf results/*
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Run static analysis and linting
lint: venv
	cppcheck --enable=all --suppress=missingInclude --inline-suppr \
		--template="{file}:{line}: {severity}: {message}" \
		firmware/src/
	$(VENV)/bin/cpplint --filter=-legal/copyright,-build/include_subdir \
		--recursive firmware/src/

# Format code
format: venv
	find firmware/src -iname "*.h" -o -iname "*.cpp" | xargs clang-format -i -style=file
	$(VENV)/bin/black run_tests.py tests/

# Run all checks
check: venv lint
	$(PYTHON) -m pytest tests/ -v

# Run tests
test: venv
	$(PYTHON) -m pytest tests/ -v

# Flash firmware
flash: venv
	$(VENV)/bin/pio run -t upload

# Install system dependencies (required only once)
install-system-deps:
	sudo apt-get update
	sudo apt-get install -y clang-format python3-venv

# Run Python linting
pylint: venv
	$(VENV)/bin/pylint run_tests.py tests/
	$(VENV)/bin/black --check run_tests.py tests/

# Development shell with all tools available
shell: venv
	@echo "Activating virtual environment..."
	@echo "Run 'deactivate' to exit"
	@bash --rcfile $(VENV)/bin/activate

.PHONY: venv install-system-deps shell 