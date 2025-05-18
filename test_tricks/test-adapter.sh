#!/usr/bin/env bash
# This script is used to run the tests from the original password-store project but using our Python implementation.
# Set TEST_ORIGINAL_PASS_VERSION to TRUE to run the tests on the original password-store.sh
# Set ONLY_ORIGINAL_TESTS to only run the original tests
# Set ONLY_ADDITIONAL_TESTS to only run the additional tests


cd "$(dirname "$0")"

rm -rf temp-test-env
mkdir temp-test-env
cp -r ../submodules/password-store/tests temp-test-env/tests
cp -r additional-tests/* temp-test-env/tests
mkdir temp-test-env/src
if [[ "${TEST_ORIGINAL_PASS_VERSION,,}" == "true" ]]; then
    echo "Running tests on original password-store.sh"
    cp ../submodules/password-store/src/password-store.sh temp-test-env/src/password-store.sh
else
    cp ../pass.py temp-test-env/src/password-store.sh
fi

cd temp-test-env/tests

if [ -n "$1" ]; then  # Run a specific test
    echo "Running test: $1"
    ./$1
    EXIT_CODE=$?
else  # Run all tests
    EXIT_CODE=0
    if [[ "${ONLY_ADDITIONAL_TESTS,,}" != "true" ]]; then
        for test in ./t[0-9][0-9][0-9][0-9]-*.sh; do
            echo "Running test: $test"
            ./$test
            if [ $? -ne 0 ]; then
                EXIT_CODE=1
            fi
        done
    fi
    if [[ "${ONLY_ORIGINAL_TESTS,,}" != "true" ]]; then
        for test in ./n[0-9][0-9][0-9][0-9]-*.sh; do
            echo "Running additional test: $test"
            ./$test
            if [ $? -ne 0 ]; then
                EXIT_CODE=1
            fi
        done
    fi
fi

cd ../..

rm -rf temp-test-env
exit $EXIT_CODE
