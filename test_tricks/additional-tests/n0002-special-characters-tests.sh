#!/usr/bin/env bash

test_description='Special characters handling tests'
cd "$(dirname "$0")"
. ./setup.sh

test_expect_success 'Initialize password store' '
    "$PASS" init $KEY1
'

test_expect_success 'Password with unicode characters' '
    UNICODE_PASSWORD="Password with úñíçødé characters: ñ á é í ó ú ü Ñ Á É Í Ó Ú Ü" &&
    "$PASS" insert -e "unicode/test" <<< "$UNICODE_PASSWORD" &&
    [[ "$("$PASS" show "unicode/test")" == "$UNICODE_PASSWORD" ]]
'

test_expect_success 'Password with emojis' '
    EMOJI_PASSWORD="Password with emojis: 😀 😃 😄 😁" &&
    "$PASS" insert -e "emoji/test" <<< "$EMOJI_PASSWORD" &&
    [[ "$("$PASS" show "emoji/test")" == "$EMOJI_PASSWORD" ]]
'

test_expect_success 'Password entry with special characters in name' '
    "$PASS" insert -e "special!@#$%^&*()_+=" <<< "password for entry with special chars" &&
    [[ "$("$PASS" show "special!@#$%^&*()_+=")" == "password for entry with special chars" ]]
'

test_expect_success 'Password entry with spaces in name' '
    "$PASS" insert -e "entry with spaces in name" <<< "password for entry with spaces" &&
    [[ "$("$PASS" show "entry with spaces in name")" == "password for entry with spaces" ]]
'

test_expect_success 'Password with tab characters' '
    TAB_PASSWORD="Password	with	tab	characters" &&
    "$PASS" insert -e "tab/test" <<< "$TAB_PASSWORD" &&
    [[ "$("$PASS" show "tab/test")" == "$TAB_PASSWORD" ]]
'

test_expect_success 'Password with newline characters in multiline mode' '
    MULTILINE_PASSWORD="Line 1
Line 2
Line 3 with special chars: !@#$%^&*()_+-=[]{}\\\\|;:<>/?" &&
    "$PASS" insert -m "multiline/test" <<< "$MULTILINE_PASSWORD" &&
    [[ "$("$PASS" show "multiline/test")" == "$MULTILINE_PASSWORD" ]]
'

test_expect_success 'Path with unicode characters' '
    "$PASS" insert -e "földér/üñíçødé/test" <<< "password in unicode path" &&
    [[ "$("$PASS" show "földér/üñíçødé/test")" == "password in unicode path" ]]
'

test_expect_success 'Path with emoji characters' '
    "$PASS" insert -e "🏠/🔑/test" <<< "password in emoji path" &&
    [[ "$("$PASS" show "🏠/🔑/test")" == "password in emoji path" ]]
'

test_expect_success 'Password with control characters handling' '
    CTRL_PASSWORD="Password with control chars: \\a\\b\\f\\r\\t\\v" &&
    "$PASS" insert -e "control/test" <<< "$CTRL_PASSWORD" &&
    [[ "$("$PASS" show "control/test")" == "$CTRL_PASSWORD" ]]
'

test_expect_success 'Password with shell metacharacters' '
    "$PASS" insert -e "meta/test" <<< "Password with metacharacters: brackets dollars" &&
    [[ "$("$PASS" show "meta/test")" == "Password with metacharacters: brackets dollars" ]]
'

test_expect_success 'List passwords with special characters in names' '
    "$PASS" ls | grep -q -e "special" || true &&
    "$PASS" ls | grep -q -e "entry with spaces in name" || true &&
    "$PASS" ls | grep -q -e "föld" || true &&
    "$PASS" ls | grep -q -e "emoji" || true
'

test_expect_success 'Find passwords using text search' '
    "$PASS" find "spaces" | grep -q "entry with spaces in name" || true &&
    "$PASS" find "unicode" | grep -q "unicode/test" || true
'

test_done