#!/bin/bash

# run_all_tests.sh - Execute all LocalBolt unit and integration tests

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "--- Running LocalBolt Test Suite ---"
export PYTHONPATH=src

FAILED=0

# List of tests to run
TESTS=(
    "tests/unit/test_asm_help.py"
    "tests/unit/test_compiler.py"
    "tests/unit/test_config.py"
    "tests/unit/test_lexer_stl.py"
    "tests/unit/test_parser.py"
    "tests/unit/test_c_app.py"
    "tests/unit/test_c_main.py"
    "tests/unit/test_c_widgets.py"
    "tests/unit/test_lang.py"
    "tests/unit/test_rust_driver.py"
    "tests/unit/test_rust_demangle.py"
    "tests/unit/test_rust_lexer.py"
    "tests/integration/test_engine.py"
    "tests/integration/test_lexer.py"
    "tests/integration/test_watcher.py"
)

for test in "${TESTS[@]}"; do
    if [ -f "$test" ]; then
        echo -n "Running $test... "
        ./.venv/bin/python3 "$test" > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}PASSED${NC}"
        else
            echo -e "${RED}FAILED${NC}"
            FAILED=$((FAILED + 1))
        fi
    else
        echo -e "Skipping $test (not found)"
    fi
done

echo "------------------------------------"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}$FAILED tests failed.${NC}"
    exit 1
fi
