import unittest
import sys

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.discover("tests", pattern="test_pipeline.py")
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    print(f"\nTEST RUN FINISHED: Ran {result.testsRun} tests, Errors: {len(result.errors)}, Failures: {len(result.failures)}")
    if not result.wasSuccessful():
        print("\nFAILURES:")
        for test, err in result.failures:
            print(f"- {test}: {err.splitlines()[-1] if err else 'failed'}")
        print("\nERRORS:")
        for test, err in result.errors:
            print(f"- {test}: {err.splitlines()[-1] if err else 'error'}")
        sys.exit(1)
    sys.exit(0)
