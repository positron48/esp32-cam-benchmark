.PHONY: all build clean lint format check test flash venv fix install install-dev

# Python virtual environment directory
VENV := .venv
PYTHON := $(VENV)/bin/python3
PIP := $(VENV)/bin/pip

# Default target
all: check build

# Create and setup virtual environment with minimal dependencies
$(VENV)/bin/activate:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install -e .
	mkdir -p results/video results/logs results/metrics

# Install package in development mode with all dev dependencies
install-dev: $(VENV)/bin/activate
	$(PIP) install -r requirements-dev.txt
	$(PIP) install -e .

# Basic installation for running benchmarks
install: $(VENV)/bin/activate

venv: install-dev

# Build firmware
build: venv
	$(VENV)/bin/pio run

# Clean build files
clean:
	$(VENV)/bin/pio run -t clean
	rm -rf .pio
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Run static analysis without fixing
lint: venv
	@echo "Running C++ checks..."
	$(VENV)/bin/cppcheck --enable=all --suppress=missingInclude --inline-suppr \
		--template="{file}:{line}: {severity}: {message}" \
		src/ 2>cppcheck_errors.txt || (cat cppcheck_errors.txt && exit 1)
	$(VENV)/bin/cpplint --filter=-legal/copyright,-build/include_subdir,-whitespace/newline,-readability/braces \
		--recursive src/
	@echo "Running Python checks..."
	$(VENV)/bin/ruff check benchmark/ tests/
	$(VENV)/bin/pylint --fail-under=8.0 benchmark/ tests/

# Check code formatting
format: venv
	@echo "Checking clang-format version..."
	@clang-format --version
	@echo "Checking C++ formatting..."
	@for file in $$(find src -iname "*.h" -o -iname "*.cpp"); do \
		if ! clang-format --dry-run --Werror --style=file:.clang-format "$$file" 2>/dev/null; then \
			echo "\nFormatting issues in $$file:"; \
			echo "Expected format:"; \
			clang-format --style=file:.clang-format "$$file"; \
			echo "\nActual file:"; \
			cat "$$file"; \
			echo "\nDiff:"; \
			clang-format --style=file:.clang-format "$$file" | diff -u "$$file" -; \
			exit 1; \
		fi \
	done
	@echo "C++ formatting is correct"
	@echo "Checking Python formatting..."
	@$(VENV)/bin/black --check benchmark/ tests/

# Run all checks without fixing
check: venv
	@echo "Running all checks..."
	@echo "1. Running C++ checks..."
	@echo "Checking C++ formatting..."
	find src -iname "*.h" -o -iname "*.cpp" | xargs clang-format --dry-run --Werror --style=file:.clang-format
	$(VENV)/bin/cppcheck --enable=all --suppress=missingInclude --inline-suppr \
		--template="{file}:{line}: {severity}: {message}" \
		src/
	$(VENV)/bin/cpplint --filter=-legal/copyright,-build/include_subdir \
		--recursive src/
	@echo "2. Running Python checks..."
	$(VENV)/bin/pylint benchmark/ tests/
	$(VENV)/bin/black --check benchmark/ tests/
	@echo "3. Running tests..."
	$(PYTHON) -m pytest tests/ -v
	@echo "Checks completed. Use 'make fix' to attempt automatic fixes."

# Attempt to fix all issues automatically
fix: venv
	@echo "Fixing code formatting..."
	@echo "1. Fixing Python code..."
	$(VENV)/bin/ruff check --fix benchmark/ tests/
	$(VENV)/bin/isort benchmark/ tests/
	$(VENV)/bin/black benchmark/ tests/
	@echo "2. Fixing C++ code..."
	@find src -iname "*.h" -o -iname "*.cpp" | xargs -r clang-format -i --style=file:.clang-format
	@echo "Fix completed. Please review changes."

# Run tests
test: venv
	$(PYTHON) -m pytest tests/ -v

# Flash firmware
flash: venv
	$(VENV)/bin/pio run -t upload

# Install system dependencies (required only once)
install-system-deps:
	sudo apt-get update
	sudo apt-get install -y python3-venv clang-format

# Run Python linting
pylint: venv
	$(VENV)/bin/pylint benchmark/ tests/
	$(VENV)/bin/black --check benchmark/ tests/

# Development shell with all tools available
shell: venv
	@echo "Activating virtual environment..."
	@echo "Run 'deactivate' to exit"
	@bash --rcfile $(VENV)/bin/activate

.PHONY: venv install install-dev install-system-deps shell