.PHONY: all build clean lint format check test flash venv fix

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
	$(PIP) install cppcheck cpplint pytest pytest-cov black pylint platformio autopep8 clang-format

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

# Run static analysis without fixing
lint: venv
	-$(VENV)/bin/cppcheck --enable=all --suppress=missingInclude --inline-suppr \
		--template="{file}:{line}: {severity}: {message}" \
		firmware/src/
	-$(VENV)/bin/cpplint --filter=-legal/copyright,-build/include_subdir \
		--recursive firmware/src/
	-$(VENV)/bin/pylint run_tests.py tests/

# Format code without checking
format: venv
	find firmware/src -iname "*.h" -o -iname "*.cpp" | xargs clang-format -i -style=file
	$(VENV)/bin/black run_tests.py tests/

# Run all checks without fixing
check: venv
	@echo "Running all checks..."
	@echo "1. Running C++ checks..."
	-$(VENV)/bin/cppcheck --enable=all --suppress=missingInclude --inline-suppr \
		--template="{file}:{line}: {severity}: {message}" \
		firmware/src/
	-$(VENV)/bin/cpplint --filter=-legal/copyright,-build/include_subdir \
		--recursive firmware/src/
	@echo "2. Running Python checks..."
	-$(VENV)/bin/pylint run_tests.py tests/
	-$(VENV)/bin/black --check run_tests.py tests/
	@echo "3. Running tests..."
	$(PYTHON) -m pytest tests/ -v
	@echo "Checks completed. Use 'make fix' to attempt automatic fixes."

# Attempt to fix all issues automatically
fix: venv
	@echo "Attempting to fix code issues..."
	@echo "1. Fixing C++ formatting..."
	find firmware/src -iname "*.h" -o -iname "*.cpp" | xargs clang-format -i -style=file
	@echo "2. Fixing Python formatting..."
	$(VENV)/bin/black run_tests.py tests/
	$(VENV)/bin/autopep8 --in-place --aggressive --aggressive run_tests.py tests/*.py
	@echo "3. Running checks after fixes..."
	@make check
	@echo "Fix completed. Please review changes and run tests."

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