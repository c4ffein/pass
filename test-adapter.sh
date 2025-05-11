#!/usr/bin/env bash
# This script is used to run the tests from the original password-store project
# but using our Python implementation.

export ORIG_PASS_SCRIPT=$(which pass)
export NEW_PASS_SCRIPT="$PWD/pass.py"

# Define test environment variables
export PASSWORD_STORE_DIR="${PASSWORD_STORE_DIR:-/tmp/pass-python-test}"
export PASSWORD_STORE_GPG_OPTS="--batch --yes"

# Run the specific test or all tests from the submodule
cd submodules/password-store/

if [ -n "$1" ]; then
    # Run a specific test
    PASS="$NEW_PASS_SCRIPT" tests/$1
else
    # Run all tests
    for test in tests/t*.sh; do
        echo "Running test: $test"
        PASS="$NEW_PASS_SCRIPT" $test
    done
fi