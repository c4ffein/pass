list-tests:
	cd submodules/password-store/tests/; ls t[0-9][0-9][0-9][0-9]-*.sh
test:
	./test_tricks/test-adapter.sh
test-t0001-sanity-checks:
	./test_tricks/test-adapter.sh t0001-sanity-checks.sh
test-t0010-generate-tests:
	./test_tricks/test-adapter.sh t0010-generate-tests.sh
test-t0020-show-tests:
	./test_tricks/test-adapter.sh t0020-show-tests.sh
test-t0050-mv-tests:
	./test_tricks/test-adapter.sh t0050-mv-tests.sh
test-t0060-rm-tests:
	./test_tricks/test-adapter.sh t0060-rm-tests.sh
test-t0100-insert-tests:
	./test_tricks/test-adapter.sh t0100-insert-tests.sh
test-t0200-edit-tests:
	./test_tricks/test-adapter.sh t0200-edit-tests.sh
test-t0300-reencryption:
	./test_tricks/test-adapter.sh t0300-reencryption.sh
test-t0400-grep:
	./test_tricks/test-adapter.sh t0400-grep.sh
test-t0500-find:
	./test_tricks/test-adapter.sh t0500-find.sh
