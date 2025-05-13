#!/usr/bin/env bash
# This script is used to run the tests from the original password-store project but using our Python implementation.


cd "$(dirname "$0")"

rm -rf temp-test-env
mkdir temp-test-env
cp -r ../submodules/password-store/tests temp-test-env/tests
cp -r ../submodules/password-store/src temp-test-env/src
cp ../pass.py temp-test-env/src/password-store.sh

cd temp-test-env/tests

if [ -n "$1" ]; then  # Run a specific test
    echo "Running test: $1"
    ./$1
else  # Run all tests
    for test in ./t[0-9][0-9][0-9][0-9]-*.sh; do
        echo "Running test: $test"
        ./$test
    done
fi

cd ../..

rm -rf temp-test-env
