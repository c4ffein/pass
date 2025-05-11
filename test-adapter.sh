#!/usr/bin/env bash
# This script is used to run the tests from the original password-store project
# but using our Python implementation.

export ORIG_PASS_SCRIPT=$(which pass)
export NEW_PASS_SCRIPT="$PWD/pass.py"
chmod +x "$NEW_PASS_SCRIPT"  # Ensure it's executable

# Define test environment variables
export PASSWORD_STORE_DIR="${PASSWORD_STORE_DIR:-/tmp/pass-python-test}"
export PASSWORD_STORE_GPG_OPTS="--batch --yes"

# Change to the tests directory
cd submodules/password-store/tests

# Create a wrapper script to intercept setup.sh
cat > override_setup.sh << EOF
#!/usr/bin/env bash
# First source the original setup
. ./setup.sh

# Then override the PASS variable with our Python implementation
PASS="$NEW_PASS_SCRIPT"
export PASS
EOF
chmod +x override_setup.sh

if [ -n "$1" ]; then
    # Run a specific test
    sed -i 's/\. \.\/setup.sh/source \.\/override_setup.sh/' ./$1
    ./$1
else
    # Run all tests
    for test in ./t*.sh; do
        echo "Running test: $test"
        # Create a temporary copy that uses our script
        test_filename=$(basename $test)
        cp $test ./temp_$test_filename
        sed -i 's/\. \.\/setup.sh/source \.\/override_setup.sh/' ./temp_$test_filename
        ./temp_$test_filename
        rm ./temp_$test_filename
    done
fi