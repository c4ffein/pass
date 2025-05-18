# pass.py - Python Password Store Implementation

This repository contains a Python implementation of [password-store](https://www.passwordstore.org/), the standard Unix password manager. The aim is to provide a single file Python script (`pass.py`) with no external dependencies that offers the same functionality as the original bash script.

## Claude Code

This implementation has been made with [Claude Code](https://github.com/anthropics/claude-code). [You can read more about how this code have been made.](chat_history/00-INDEX.md)

## Features

- No external Python dependencies, only uses standard library modules
- Fully compatible with the original pass command-line interface
- Supports all the original functionality including:
  - Password generation
  - Encryption/decryption using GPG
  - Git integration for version control
  - Tree-based password listing
  - Clipboard and QR code support

## Dependencies

The Python implementation has the same system dependencies as the original:

- GnuPG2
- git
- xclip (for X11 environments)
- wl-clipboard (for Wayland environments)
- tree >= 1.7.0
- GNU getopt
- qrencode (optional, for QR code support)

## Usage

The `pass.py` script can be used as a drop-in replacement for the original `pass` command:

```bash
# Initialize a password store with your GPG key ID
./pass.py init <gpg-id>

# Add a new password
./pass.py insert <pass-name>

# Generate a new password
./pass.py generate <pass-name> [pass-length]

# Show a password
./pass.py show <pass-name>

# Edit a password
./pass.py edit <pass-name>

# Remove a password
./pass.py rm <pass-name>

# List all passwords
./pass.py ls
```

## Testing

The Python implementation is designed to be fully compatible with the original bash script and should pass all the tests in `submodules/password-store/tests/`. Additional tests have also been written in an automated way, see [the documentation about Claude Code](chat_history/00-INDEX.md)

- `make test` tests the Python implementation against both the original test suite and additional tests
- `make list-test` lists the available tests, including both the original and additional test suites
- `make diff-tests-list` show tests that are still not included in the Makefile, or missing in your files
- `make test-t0001-sanity-checks` run a specific test file
- `TEST_ORIGINAL_PASS_VERSION=TRUE make test` run the test suite against the original `password-store.sh`
  - `TEST_ORIGINAL_PASS_VERSION=TRUE make test-t0001-sanity-checks` also works with specific tests
- `ONLY_ORIGINAL_TESTS=TRUE make test` test only against the original test suite, unhandled by file-specific tests
- `ONLY_ADDITIONAL_TESTS=TRUE make test` test only against the additional test suite, unhandled by file-specific tests

```bash
# Run all tests using the Python implementation
./test-adapter.sh

# Run a specific test
./test-adapter.sh t0001-sanity-checks.sh
```

## Project Structure

- `pass.py`: The Python implementation of password-store
- `test-adapter.sh`: A script to run the original test suite with the Python implementation
- `submodules/password-store/`: The original password-store bash implementation (included as a git submodule)

## License

This project is licensed under the GPL-2.0+ license, the same as the original password-store.
