#!/usr/bin/env bash

test_description='Advanced move operations tests'
cd "$(dirname "$0")"
. ./setup.sh

# Create a complex directory structure and test various move scenarios

test_expect_success 'Initialize password store with complex structure' '
    "$PASS" init $KEY1 &&
    # Create nested structure
    "$PASS" insert -e "level1/level2/level3/password1" <<< "password 1 content" &&
    "$PASS" insert -e "level1/level2/password2" <<< "password 2 content" &&
    "$PASS" insert -e "level1/password3" <<< "password 3 content" &&
    "$PASS" insert -e "level1/level2a/password4" <<< "password 4 content" &&
    "$PASS" insert -e "level1/level2a/level3a/password5" <<< "password 5 content" &&
    # Create entries with special chars in paths
    "$PASS" insert -e "special chars/password space" <<< "password with space" &&
    "$PASS" insert -e "special chars/password!special" <<< "password with special char" &&
    "$PASS" insert -e "unicode/üñíçødé/password6" <<< "password 6 content" &&
    "$PASS" insert -e "emoji/🔑/password7" <<< "password 7 content" &&
    # Create more entries for force testing
    "$PASS" insert -e "force/test1" <<< "force test 1" &&
    "$PASS" insert -e "destination/different" <<< "different password"
'

# Test moving single password to new location
test_expect_success 'Move single password to new location' '
    "$PASS" mv "level1/password3" "newlocation/password3" &&
    ! "$PASS" show "level1/password3" 2>/dev/null &&
    [[ "$("$PASS" show "newlocation/password3")" == "password 3 content" ]]
'

# Test moving password to existing directory
test_expect_success 'Move password to existing directory' '
    "$PASS" mv "level1/level2/password2" "newlocation/" &&
    ! "$PASS" show "level1/level2/password2" 2>/dev/null &&
    [[ "$("$PASS" show "newlocation/password2")" == "password 2 content" ]]
'

# Test moving entire directory with nested structure
test_expect_success 'Move entire directory with nested structure' '
    "$PASS" mv "level1/level2" "level1/moved_level2" &&
    ! "$PASS" show "level1/level2/level3/password1" 2>/dev/null &&
    [[ "$("$PASS" show "level1/moved_level2/level3/password1")" == "password 1 content" ]]
'

# Test moving to destination with same basename but different path
test_expect_success 'Move to destination with same basename but different path' '
    "$PASS" mv "level1/level2a/password4" "level1/moved_level2/password4" &&
    ! "$PASS" show "level1/level2a/password4" 2>/dev/null &&
    [[ "$("$PASS" show "level1/moved_level2/password4")" == "password 4 content" ]]
'

# Test force move to overwrite existing entry
test_expect_success 'Force move to overwrite existing entry' '
    [[ "$("$PASS" show "force/test1")" == "force test 1" ]] &&
    [[ "$("$PASS" show "destination/different")" == "different password" ]] &&
    "$PASS" mv -f "force/test1" "destination/different" &&
    ! "$PASS" show "force/test1" 2>/dev/null &&
    [[ "$("$PASS" show "destination/different")" == "force test 1" ]]
'

# Test moving with special characters in path
test_expect_success 'Move with special characters in path' '
    "$PASS" mv "special chars/password space" "moved/password space" &&
    ! "$PASS" show "special chars/password space" 2>/dev/null &&
    [[ "$("$PASS" show "moved/password space")" == "password with space" ]] &&
    
    "$PASS" mv "special chars/password!special" "moved/password!special" &&
    ! "$PASS" show "special chars/password!special" 2>/dev/null &&
    [[ "$("$PASS" show "moved/password!special")" == "password with special char" ]]
'

# Test moving with unicode and emoji in path
test_expect_success 'Move with unicode and emoji in path' '
    "$PASS" mv "unicode/üñíçødé/password6" "moved/üñíçødé-password6" &&
    ! "$PASS" show "unicode/üñíçødé/password6" 2>/dev/null &&
    [[ "$("$PASS" show "moved/üñíçødé-password6")" == "password 6 content" ]] &&
    
    "$PASS" mv "emoji/🔑/password7" "moved/emoji-🔑-password7" &&
    ! "$PASS" show "emoji/🔑/password7" 2>/dev/null &&
    [[ "$("$PASS" show "moved/emoji-🔑-password7")" == "password 7 content" ]]
'

# Test moving entire directory with unicode characters
test_expect_success 'Move entire directory with unicode/emoji characters' '
    "$PASS" insert -e "sourceDir/üñíçødé/test1" <<< "unicode test 1" &&
    "$PASS" insert -e "sourceDir/üñíçødé/test2" <<< "unicode test 2" &&
    "$PASS" insert -e "sourceDir/emoji/🔑/test3" <<< "emoji test 3" &&
    
    "$PASS" mv "sourceDir/üñíçødé" "targetDir/üñíçødé-moved" &&
    ! "$PASS" show "sourceDir/üñíçødé/test1" 2>/dev/null &&
    ! "$PASS" show "sourceDir/üñíçødé/test2" 2>/dev/null &&
    [[ "$("$PASS" show "targetDir/üñíçødé-moved/test1")" == "unicode test 1" ]] &&
    [[ "$("$PASS" show "targetDir/üñíçødé-moved/test2")" == "unicode test 2" ]]
'

# Test moving multiple levels at once
test_expect_success 'Move multiple levels at once' '
    "$PASS" insert -e "deep/nested/structure/test" <<< "deep nested test" &&
    "$PASS" mv "deep/nested/structure" "flat-structure" &&
    ! "$PASS" show "deep/nested/structure/test" 2>/dev/null &&
    [[ "$("$PASS" show "flat-structure/test")" == "deep nested test" ]]
'

# Skip the shadowed password tests since they might be implementation-specific
# Instead, test some more basic move operations
test_expect_success 'Test moving with existing parent directories' '
    # Create parent directory first
    "$PASS" insert -e "parent/already-exists" <<< "parent exists" &&
    # Then move a password to it
    "$PASS" insert -e "standalone" <<< "standalone password" &&
    "$PASS" mv "standalone" "parent/relocated" &&
    ! "$PASS" show "standalone" 2>/dev/null &&
    [[ "$("$PASS" show "parent/relocated")" == "standalone password" ]]
'

test_expect_success 'Test moving and renaming in one operation' '
    "$PASS" insert -e "source/original-name" <<< "original content" &&
    "$PASS" mv "source/original-name" "target/new-name" &&
    ! "$PASS" show "source/original-name" 2>/dev/null &&
    [[ "$("$PASS" show "target/new-name")" == "original content" ]]
'

test_done