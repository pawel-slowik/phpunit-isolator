#!/usr/bin/env python3

import re
import subprocess
import xml.etree.ElementTree as ET
from typing import Iterable, NamedTuple, Optional


class Test(NamedTuple):
    class_: str
    method: str
    data_set: Optional[str]

    def as_filter(self) -> str:
        return re.escape(self.class_) + "::" + self.method + self.data_set_as_filter()

    def data_set_as_filter(self) -> str:
        if self.data_set is None:
            return ""
        if re.fullmatch("#[0-9]+", self.data_set):
            return self.data_set
        return " with data set " + re.escape(self.data_set)


class TestResult(NamedTuple):
    passed: bool
    output: str


def list_tests() -> Iterable[Test]:
    list_command = [
        "./vendor/bin/phpunit",
        "--list-tests-xml",
        "php://stderr",
    ]
    process = subprocess.run(list_command, capture_output=True, check=True, text=True)
    yield from list_tests_from_xml(process.stderr)


def list_tests_from_xml(xml: str) -> Iterable[Test]:
    doc = ET.fromstring(xml)
    for class_node in doc.findall("testCaseClass"):
        for method_node in class_node.findall("testCaseMethod"):
            yield Test(
                class_=class_node.attrib["name"],
                method=method_node.attrib["name"],
                data_set=method_node.attrib.get("dataSet"),
            )


def run_test(test: Test) -> TestResult:
    run_command = [
        "./vendor/bin/phpunit",
        "--fail-on-warning",
        "--fail-on-risky",
        "--no-coverage",
        "--filter",
        test.as_filter(),
    ]
    try:
        process = subprocess.run(run_command, capture_output=True, check=True, text=True)
        return TestResult(passed=test_output_is_ok(process.stdout), output=process.stdout)
    except subprocess.CalledProcessError as ex:
        return TestResult(passed=False, output=ex.stdout)


def test_output_is_ok(test_output: str) -> bool:
    return test_output.splitlines(keepends=False)[-1].startswith("OK ")


def main():
    fail_count = 0
    for test in list_tests():
        result = run_test(test)
        if not result.passed:
            fail_count += 1
            print("test failed:")
            print(test.as_filter())
            print(result.output)
            print("-" * 40)
    print("isolated failures: %d" % fail_count)


if __name__ == "__main__":
    main()
