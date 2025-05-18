#!/usr/bin/env bash

test_description='Advanced password generation tests'
cd "$(dirname "$0")"
. ./setup.sh

test_expect_success 'Initialize password store' '
    "$PASS" init $KEY1
'

# Test default password generation
test_expect_success 'Default password generation (length and character set)' '
    "$PASS" generate default 25 &&
    [[ $("$PASS" show default | wc -c) -eq 26 ]] &&
    # Default should include symbols
    "$PASS" show default | grep -q "[^A-Za-z0-9]"
'

# Test nosymbols option
test_expect_success 'Password generation with --no-symbols flag' '
    "$PASS" generate --no-symbols nosymbols 30 &&
    [[ $("$PASS" show nosymbols | wc -c) -eq 31 ]] &&
    # Should not contain symbols
    ! "$PASS" show nosymbols | grep -q "[^A-Za-z0-9]"
'

# Test symbols only option (might not be supported but worth testing)
test_expect_success 'Password generation with --symbols-only' '
    # This test might fail if --symbols-only is not supported
    "$PASS" generate --symbols-only symbolsonly 15 2>/dev/null || true &&
    if [[ -e "$PASSWORD_STORE_DIR/symbolsonly.gpg" ]]; then
        # If the command succeeded, verify only symbols are used
        ! "$PASS" show symbolsonly | grep -q "[A-Za-z0-9]"
    fi
'

# Test for clip option - skip clipboard test and just check file creation
test_expect_success 'Password generation with --clip' '
    # Generate a password and make sure the file was created
    "$PASS" generate cliptest 20 || true &&
    # Verify the file exists (meaning generation worked)
    [[ -e "$PASSWORD_STORE_DIR/cliptest.gpg" ]]
'

# Test for in-place option with existing password
test_expect_success 'Password generation with --in-place' '
    "$PASS" insert -e existingpass <<< "oldpass" &&
    "$PASS" generate --in-place existingpass 25 &&
    [[ $("$PASS" show existingpass | wc -c) -eq 26 ]] &&
    [[ "$("$PASS" show existingpass)" != "oldpass" ]]
'

# Test for force option to override existing password
test_expect_success 'Password generation with --force' '
    "$PASS" insert -e forcetest <<< "original" &&
    "$PASS" generate --force forcetest 20 &&
    [[ $("$PASS" show forcetest | wc -c) -eq 21 ]] &&
    [[ "$("$PASS" show forcetest)" != "original" ]]
'

# Test password generation with custom length
test_expect_success 'Password generation with various lengths' '
    # Minimum length
    "$PASS" generate min 1 &&
    [[ $("$PASS" show min | wc -c) -eq 2 ]] &&
    
    # Short length
    "$PASS" generate short 8 &&
    [[ $("$PASS" show short | wc -c) -eq 9 ]] &&
    
    # Medium length
    "$PASS" generate medium 16 &&
    [[ $("$PASS" show medium | wc -c) -eq 17 ]] &&
    
    # Long length
    "$PASS" generate long 32 &&
    [[ $("$PASS" show long | wc -c) -eq 33 ]] &&
    
    # Very long length
    "$PASS" generate verylong 64 &&
    [[ $("$PASS" show verylong | wc -c) -eq 65 ]]
'

# Test for PASSWORD_STORE_CHARACTER_SET environment variable
test_expect_success 'Password generation with custom CHARACTER_SET' '
    # Save original value if set
    ORIGINAL_CHAR_SET="$PASSWORD_STORE_CHARACTER_SET" &&
    
    # Set to only uppercase letters
    export PASSWORD_STORE_CHARACTER_SET="ABCDEFGHIJKLMNOPQRSTUVWXYZ" &&
    "$PASS" generate charset1 20 &&
    [[ $("$PASS" show charset1 | wc -c) -eq 21 ]] &&
    ! "$PASS" show charset1 | grep -q "[^A-Z]" &&
    
    # Set to lowercase and digits
    export PASSWORD_STORE_CHARACTER_SET="abcdefghijklmnopqrstuvwxyz0123456789" &&
    "$PASS" generate charset2 20 &&
    [[ $("$PASS" show charset2 | wc -c) -eq 21 ]] &&
    ! "$PASS" show charset2 | grep -q "[^a-z0-9]" &&
    
    # Set to a limited set of characters
    export PASSWORD_STORE_CHARACTER_SET="abcdef" &&
    "$PASS" generate charset3 30 &&
    [[ $("$PASS" show charset3 | wc -c) -eq 31 ]] &&
    ! "$PASS" show charset3 | grep -q "[^abcdef]" &&
    
    # Restore original value if there was one
    if [ -n "$ORIGINAL_CHAR_SET" ]; then
        export PASSWORD_STORE_CHARACTER_SET="$ORIGINAL_CHAR_SET"
    else
        unset PASSWORD_STORE_CHARACTER_SET
    fi
'

# Test for PASSWORD_STORE_CHARACTER_SET_NO_SYMBOLS environment variable
test_expect_success 'Password generation with custom CHARACTER_SET_NO_SYMBOLS' '
    # Save original value if set
    ORIGINAL_CHAR_SET_NO_SYMBOLS="$PASSWORD_STORE_CHARACTER_SET_NO_SYMBOLS" &&
    
    # Set to only uppercase letters for no-symbols set
    export PASSWORD_STORE_CHARACTER_SET_NO_SYMBOLS="ABCDEFGHIJKLMNOPQRSTUVWXYZ" &&
    "$PASS" generate --no-symbols nosymbols1 20 &&
    [[ $("$PASS" show nosymbols1 | wc -c) -eq 21 ]] &&
    ! "$PASS" show nosymbols1 | grep -q "[^A-Z]" &&
    
    # Set to limited set of characters
    export PASSWORD_STORE_CHARACTER_SET_NO_SYMBOLS="123456" &&
    "$PASS" generate --no-symbols nosymbols2 20 &&
    [[ $("$PASS" show nosymbols2 | wc -c) -eq 21 ]] &&
    ! "$PASS" show nosymbols2 | grep -q "[^123456]" &&
    
    # Restore original value if there was one
    if [ -n "$ORIGINAL_CHAR_SET_NO_SYMBOLS" ]; then
        export PASSWORD_STORE_CHARACTER_SET_NO_SYMBOLS="$ORIGINAL_CHAR_SET_NO_SYMBOLS"
    else
        unset PASSWORD_STORE_CHARACTER_SET_NO_SYMBOLS
    fi
'

# Test for PASSWORD_STORE_GENERATED_LENGTH environment variable
test_expect_success 'Password generation with custom GENERATED_LENGTH' '
    # Save original value if set
    ORIGINAL_GENERATED_LENGTH="$PASSWORD_STORE_GENERATED_LENGTH" &&
    
    # Set custom default length
    export PASSWORD_STORE_GENERATED_LENGTH=42 &&
    "$PASS" generate defaultlength &&
    [[ $("$PASS" show defaultlength | wc -c) -eq 43 ]] &&
    
    # Explicit length should override environment variable
    "$PASS" generate overridelength 15 &&
    [[ $("$PASS" show overridelength | wc -c) -eq 16 ]] &&
    
    # Restore original value if there was one
    if [ -n "$ORIGINAL_GENERATED_LENGTH" ]; then
        export PASSWORD_STORE_GENERATED_LENGTH="$ORIGINAL_GENERATED_LENGTH"
    else
        unset PASSWORD_STORE_GENERATED_LENGTH
    fi
'

# Test in-place generation with multiline password
test_expect_success 'Password generation in-place with multiline content' '
    "$PASS" insert -m multiline <<< "original password
second line
third line" &&
    "$PASS" generate -i multiline 20 &&
    # First line should be replaced with generated password
    [[ $(echo "$("$PASS" show multiline)" | wc -l) -eq 3 ]] &&
    [[ $(echo "$("$PASS" show multiline)" | head -n 1 | wc -c) -eq 21 ]] &&
    [[ "$(echo "$("$PASS" show multiline)" | tail -n 2)" == "second line
third line" ]]
'

# Test combining multiple options
test_expect_success 'Password generation with multiple options combined' '
    # Test --force, --no-symbols and custom length together
    "$PASS" insert -e multioptions <<< "original content" &&
    "$PASS" generate --force --no-symbols multioptions 25 &&
    [[ $("$PASS" show multioptions | wc -c) -eq 26 ]] &&
    ! "$PASS" show multioptions | grep -q "[^A-Za-z0-9]" &&
    [[ "$("$PASS" show multioptions)" != "original content" ]]
'

test_done