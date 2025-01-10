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
	$(PIP) install cppcheck cpplint pytest pytest-cov black pylint platformio autopep8 clang-format isort autoflake pyupgrade ruff
	mkdir -p results/video results/logs results/metrics

venv: $(VENV)/bin/activate

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
	$(VENV)/bin/ruff check run_tests.py tests/
	$(VENV)/bin/pylint --fail-under=8.0 run_tests.py tests/

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
	@$(VENV)/bin/black --check run_tests.py tests/

# Run all checks without fixing
check: venv
	@echo "Running all checks..."
	@echo "1. Running C++ checks..."
	@echo "Checking C++ formatting..."
	find src -iname "*.h" -o -iname "*.cpp" | xargs clang-format --dry-run --Werror --style=file:.clang-format
	-$(VENV)/bin/cppcheck --enable=all --suppress=missingInclude --inline-suppr \
		--template="{file}:{line}: {severity}: {message}" \
		src/
	-$(VENV)/bin/cpplint --filter=-legal/copyright,-build/include_subdir \
		--recursive src/
	@echo "2. Running Python checks..."
	-$(VENV)/bin/pylint run_tests.py tests/
	-$(VENV)/bin/black --check run_tests.py tests/
	@echo "3. Running tests..."
	$(PYTHON) -m pytest tests/ -v
	@echo "Checks completed. Use 'make fix' to attempt automatic fixes."

# Attempt to fix all issues automatically
fix: venv
	@echo "Attempting to fix code issues..."
	@echo "1. Fixing C++ formatting and issues..."
	@find src -iname "*.h" -o -iname "*.cpp" | xargs -r clang-format -i --style=file:.clang-format
	$(VENV)/bin/cppcheck --enable=all --suppress=missingInclude --inline-suppr \
		--template="{file}:{line}: {severity}: {message}" \
		src/ 2>cppcheck_errors.txt
	@echo "2. Fixing Python code..."
	# Sort imports
	$(VENV)/bin/isort run_tests.py tests/
	# Remove unused imports and variables
	$(VENV)/bin/autoflake --in-place --remove-all-unused-imports --remove-unused-variables run_tests.py tests/*.py
	# Upgrade Python syntax
	$(VENV)/bin/pyupgrade --py38-plus run_tests.py tests/*.py
	# Fix common Python issues with ruff
	$(VENV)/bin/ruff check --fix run_tests.py tests/
	# Format code
	$(VENV)/bin/black run_tests.py tests/
	$(VENV)/bin/autopep8 --in-place --aggressive --aggressive run_tests.py tests/*.py
	@echo "3. Running format..."
	@echo "Formatting C++ code again to ensure consistency..."
	@find src -iname "*.h" -o -iname "*.cpp" | xargs -r clang-format -i --style=file:.clang-format
	@echo "Formatting Python code again to ensure consistency..."
	@$(VENV)/bin/black run_tests.py tests/
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
	sudo apt-get install -y python3-venv clang-format

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