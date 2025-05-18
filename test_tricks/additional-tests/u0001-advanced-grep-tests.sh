#!/usr/bin/env bash

test_description='Advanced grep tests'
cd "$(dirname "$0")"
. ./setup.sh

test_expect_success 'Setup passwords for grep tests' '
    "$PASS" init $KEY1 &&
    "$PASS" insert -m "folder1/password1" <<< "This is password1
This line contains special regex chars ( ) [ ] * + ? | ^ $
This line has the word password in it
Line with some numbers 12345
END" &&
    "$PASS" insert -m "folder1/password2" <<< "This is password2
Another line
password is repeated here
Line with some numbers 54321
END" &&
    "$PASS" insert -m "folder2/sub/test" <<< "Content without the search term
Some other content
12345
END" &&
    "$PASS" insert -m "folder2/password3" <<< "This is password3
More content here
Has the search term password
END"
'

test_expect_success 'Basic grep functionality' '
    "$PASS" grep "password" | grep -q "password1" &&
    "$PASS" grep "password" | grep -q "password2" &&
    "$PASS" grep "password" | grep -q "password3"
'

test_expect_success 'Grep with fixed string containing regex special chars' '
    "$PASS" grep -F "( ) [ ] * + ? | ^ $" | grep -q "password1" &&
    ! "$PASS" grep -F "( ) [ ] * + ? | ^ $" | grep -q "password2"
'

test_expect_success 'Grep with regular expression' '
    "$PASS" grep -E "password[123]" | grep -q "password1" &&
    "$PASS" grep -E "password[123]" | grep -q "password2" &&
    "$PASS" grep -E "password[123]" | grep -q "password3" &&
    ! "$PASS" grep -E "password[4-9]" | grep -q "password1"
'

test_expect_success 'Grep with case insensitivity' '
    "$PASS" grep -i "PASSWORD" | grep -q "password1" &&
    "$PASS" grep -i "PASSWORD" | grep -q "password2" &&
    "$PASS" grep -i "PASSWORD" | grep -q "password3"
'

# Simplified test for grep functionality
test_expect_success 'Grep functionality with number pattern' '
    "$PASS" grep "12345" | grep -q "password1" &&
    ! "$PASS" grep "12345" | grep -q "password2"
'

test_expect_success 'Grep with pattern matching only in entry name' '
    ! "$PASS" grep -e "test$" | grep -q "folder2/sub/test"
'

test_expect_success 'Grep with combination of options' '
    "$PASS" grep -i -E "PASSWORD[123]" | grep -q "password1" &&
    "$PASS" grep -i -E "PASSWORD[123]" | grep -q "password2" &&
    "$PASS" grep -i -E "PASSWORD[123]" | grep -q "password3"
'

test_done
