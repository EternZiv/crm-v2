import os
import time
import traceback


def step(name, fn):
    started = time.perf_counter()
    print("BEGIN", name, flush=True)
    try:
        value = fn()
        print("DONE", name, round(time.perf_counter() - started, 3), flush=True)
        return value
    except BaseException as exc:
        print("ERROR", name, type(exc).__name__, str(exc)[:500], flush=True)
        traceback.print_exc()
        raise


step("python_import_django", lambda: __import__("django"))
os.environ["DJANGO_SETTINGS_MODULE"] = "finlo.settings.security_test"
step("django_setup", lambda: __import__("django").setup())
step("import_export_tests", lambda: __import__("finlo.contrib.core.test_export_optimization"))
from django.conf import settings
from django.test.utils import get_runner

runner_cls = step("get_runner", lambda: get_runner(settings))
runner = runner_cls(verbosity=2, interactive=False, keepdb=False)
step("test_runner_setup", runner.setup_test_environment)
old_config = step("setup_databases", runner.setup_databases)
try:
    suite = step(
        "build_suite",
        lambda: runner.build_suite(["finlo.contrib.core.test_export_optimization"]),
    )
    print("SUITE_COUNT", suite.countTestCases(), flush=True)
    result = step("run_suite", lambda: runner.run_suite(suite))
    print("RESULT", result.wasSuccessful(), result.testsRun, flush=True)
finally:
    step("teardown_databases", lambda: runner.teardown_databases(old_config))
    runner.teardown_test_environment()
