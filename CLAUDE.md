# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Structure

This repository contains the `password-store` project, which is included as a git submodule in `submodules/password-store`. `password-store` is a simple command-line password manager that uses GPG for encryption and Git for version control.

The aim of this repository is to provide a single file python script `pass.py` without any dependency to any external library, that replaces the `password-store` bash script. The python implementation is designed to be fully compatible with the original bash script and should pass all the tests in `submodules/password-store/tests/t0*.sh`.

## Python Implementation

The `pass.py` script provides a Python implementation of the password-store functionality with the following features:

- No external Python dependencies, only uses standard library modules
- Fully compatible with the original pass command-line interface
- Supports all the original functionality including:
  - Password generation
  - Encryption/decryption using GPG
  - Git integration for version control
  - Tree-based password listing
  - Clipboard and QR code support

### Testing the Python Implementation

To test the Python implementation against the original test suite:

```bash
# Run all tests using the Python implementation
./test_tricks/test-adapter.sh

# Run a specific test
./test_tricks/test-adapter.sh t0001-sanity-checks.sh
```

The test adapter sets the necessary environment variables and uses the Python implementation instead of the original bash script when running the tests.

You can run the tests against the original `password-store.sh` by using `TEST_ORIGINAL_PASS_VERSION=TRUE ./test_tricks/test-adapter.sh`

### Using Password Store

Here are some common commands for using the password manager:

```bash
# Initialize a password store with your GPG key ID
pass init <gpg-id>

# Add a new password
pass insert <pass-name>

# Generate a new password
pass generate <pass-name> [pass-length]

# Show a password
pass show <pass-name>

# Edit a password
pass edit <pass-name>

# Remove a password
pass rm <pass-name>

# List all passwords
pass ls
```

## Dependencies

Password Store depends on:
- bash
- GnuPG2
- git
- xclip (for X11 environments)
- wl-clipboard (for Wayland environments)
- tree >= 1.7.0
- GNU getopt
- qrencode (optional, for QR code support)
