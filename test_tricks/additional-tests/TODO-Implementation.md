# Implementation TODOs for Python Version

Based on our additional tests, we've identified the following functionality that needs to be implemented or fixed in the Python version:

## Grep Functionality

1. **Regular Expression Support**
   - The Python implementation needs to properly support the `-E` flag for regular expressions in the `grep` command
   - Regular expressions should work with character classes (`[123]`) and ranges (`[4-9]`)
   - Test failures: `Grep with regular expression` and `Grep with combination of options`

2. **Combined Options**
   - Support for combining multiple grep options (like `-i -E` for case-insensitive regex search)

## Password Generation

1. **In-place Generation**
   - The `--in-place` option for the `generate` command needs fixing
   - This should replace just the first line of a password file while preserving other lines
   - Test failure: `Password generation with --in-place`

2. **Character Set Handling**
   - Ensure proper support for environment variables:
     - `PASSWORD_STORE_CHARACTER_SET`
     - `PASSWORD_STORE_CHARACTER_SET_NO_SYMBOLS`
     - `PASSWORD_STORE_GENERATED_LENGTH`

3. **Symbols-only Option**
   - Support for the `--symbols-only` flag if implemented in the original

## Unicode and Special Characters

All tests for Unicode and special characters are currently passing, which means the Python implementation has good support for:

1. Unicode characters in passwords and paths
2. Emoji characters in passwords and paths
3. Special characters in entry names
4. Spaces in entry names
5. Tab and newline characters in passwords

## Move Command

All tests for the move command are passing, showing good support for:

1. Moving single passwords to new locations
2. Moving passwords to existing directories
3. Moving entire directories with nested structures
4. Force-moving to overwrite existing entries
5. Moving paths with special characters, Unicode, and emoji

This document identifies the main areas that need attention to ensure full compatibility with the original password-store.sh implementation.
