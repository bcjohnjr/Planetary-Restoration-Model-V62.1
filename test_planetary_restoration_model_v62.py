#!/usr/bin/env python3
from planetary_restoration_model_v62 import run_v62, run_tests, completeness_check


def main():
    result = run_v62()
    run_tests(result)
    check = completeness_check(result)
    assert check["pass"]
    print("PASS", check)


if __name__ == "__main__":
    main()
