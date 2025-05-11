# pass.py - Python Password Store Implementation

This repository contains a Python implementation of [password-store](https://www.passwordstore.org/), the standard Unix password manager. The aim is to provide a single file Python script (`pass.py`) with no external dependencies that offers the same functionality as the original bash script.

## Claude Code

This implementation has been made with [Claude Code](https://github.com/anthropics/claude-code). All I did was:
- Load the initial implementation in a submodule (in case we may want to update the test suite...) so that he had access to both the initial implementation and the tests.
- Let him generate the initial `CLAUDE.md` file, he understood very well the structure of this repository and described it in quite a straightforward way.
- Added a few short sentences about what I wanted us to do.
- Asked `> I updated the CLAUDE.md file. What should we do now?`
- After that, I only said yes to everything. Some tests still don't pass, but those are edge cases. He did follow my recommendations, and built the perfect adapter to run the tests in the original submodule with the new `pass.py` he just built

Obviously, this is just a quick experiment for now, but I didn't expect things to work as much as they did. I'll just drop a `CHAT_HISTORY.md` file if you are curious about our conversation.

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

The Python implementation is designed to be fully compatible with the original bash script and should pass all the tests in `submodules/password-store/tests/`.

To test the Python implementation against the original test suite:

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
