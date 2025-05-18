list-tests:
	cd submodules/password-store/tests; ls t[0-9][0-9][0-9][0-9]-*.sh
diff-tests-list:
	bash -c 'diff <(grep test-t[0-9][0-9][0-9][0-9]-.* Makefile | cut -c6- | grep -o ".*[^:]") <(for f in submodules/password-store/tests/t[0-9][0-9][0-9][0-9]-*.sh; do echo "$${f%.sh}" | cut -c33-; done)'
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
test-u0001-advanced-grep-tests:
	./test_tricks/test-adapter.sh u0001-advanced-grep-tests.sh
test-u0002-special-characters-tests:
	./test_tricks/test-adapter.sh u0002-special-characters-tests.sh
test-u0003-complex-move-tests:
	./test_tricks/test-adapter.sh u0003-complex-move-tests.sh
test-u0004-password-generation-options:
	./test_tricks/test-adapter.sh u0004-password-generation-options.sh
