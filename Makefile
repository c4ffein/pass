TESTS_DIR ?= submodules/password-store/tests

list-tests:
	cd $(TESTS_DIR); ls t[0-9][0-9][0-9][0-9]-*.sh
list-missing-tests:
	@echo "Checking for tests not in Makefile..."
	@cd $(TESTS_DIR) && ls t[0-9][0-9][0-9][0-9]-*.sh | sed 's/\.sh$$//' > /tmp/all_tests.txt
	@grep -o 'test-t[0-9][0-9][0-9][0-9]-[^:]*' $(MAKEFILE_LIST) | sed 's/test-//' > /tmp/makefile_tests.txt
	@echo "Directory: $(TESTS_DIR)"
	@echo "Found $$(wc -l < /tmp/all_tests.txt) tests in directory"
	@echo "Found $$(wc -l < /tmp/makefile_tests.txt) tests in Makefile"
	@if ! grep -vxf /tmp/makefile_tests.txt /tmp/all_tests.txt > /tmp/missing_tests.txt; then \
		echo "All tests are already included in the Makefile."; \
	elif [ ! -s /tmp/missing_tests.txt ]; then \
		echo "All tests are already included in the Makefile."; \
	else \
		echo "Tests in directory but missing from Makefile:"; \
		cat /tmp/missing_tests.txt; \
	fi
	@rm -f /tmp/all_tests.txt /tmp/makefile_tests.txt /tmp/missing_tests.txt

generate-missing-test-targets:
	@echo "Generating Makefile targets for missing tests..."
	@cd $(TESTS_DIR) && ls t[0-9][0-9][0-9][0-9]-*.sh | sed 's/\.sh$$//' > /tmp/all_tests.txt
	@grep -o 'test-t[0-9][0-9][0-9][0-9]-[^:]*' $(MAKEFILE_LIST) | sed 's/test-//' > /tmp/makefile_tests.txt
	@if ! grep -vxf /tmp/makefile_tests.txt /tmp/all_tests.txt > /tmp/missing_tests.txt || [ ! -s /tmp/missing_tests.txt ]; then \
		echo "No missing tests to generate targets for."; \
	else \
		echo "# Add these targets to your Makefile:"; \
		while read test; do \
			echo "test-$$test:"; \
			echo "	./test_tricks/test-adapter.sh $$test.sh"; \
		done < /tmp/missing_tests.txt; \
	fi
	@rm -f /tmp/all_tests.txt /tmp/makefile_tests.txt /tmp/missing_tests.txt
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
