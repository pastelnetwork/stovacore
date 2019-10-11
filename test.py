import unittest

import tests


if __name__ == "__main__":
    results = unittest.TestResult()

    print("Discovering tests")
    loader = unittest.TestLoader()
    all_tests = loader.loadTestsFromModule(tests)

    print("Found %s test cases" % all_tests.countTestCases())
    all_tests.run(results)

    print("#" * 100)
    if results.wasSuccessful():
        msg = "SUCCESSFULLY"
    else:
        msg = "WITH ERRORS"

    print("Test results ran %s:\n\tErrors: %s\n\tFailures: %s\n\tSkipped: %s" % (
        msg, len(results.errors), len(results.failures), len(results.skipped)))

    for module, error in results.errors:
        print("\tERROR in %s: %s" % (module, error))
    for module, failure in results.failures:
        print("\tFAILURE in %s: %s" % (module, failure))
    for module, skipped in results.skipped:
        print("\tSKIPPED in %s: %s" % (module, skipped))

    print("#" * 100)
