#!/usr/bin/env bash
# Tests each function separately, and gracefully to avoid trigger security

set -e
TEST_API_FUNCTIONS=(
    TestAPI.test_delete_file
    TestAPI.test_add_delete_task_bt
    TestAPI.test_tasks_directories
    TestAPI.test_search
    TestPrivateAPI
    TestCookies
)


for f in "${TEST_API_FUNCTIONS[@]}"; do
    printf '%.0s=' {1..80}; echo
    echo $f
    nosetests tests.test_api:$f
done
