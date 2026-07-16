"""Standard-library statement coverage for the dependency-free reference service."""

import ast
import json
import sys
import trace
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src" / "ticketplus"
CRITICAL_MODULES = {"checkout.py", "events.py", "reservation.py"}


def executable_lines(path: Path) -> set[int]:
    tree = ast.parse(path.read_text(), filename=str(path))
    return {
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.stmt)
        and not (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        )
    }


def main() -> int:
    sys.path.insert(0, str(ROOT / "src"))
    tracer = trace.Trace(count=True, trace=False, ignoredirs=[sys.prefix, sys.base_prefix])
    test_result = tracer.runfunc(run_tests)
    counts = tracer.results().counts

    modules = []
    total_executable = 0
    total_covered = 0
    for path in sorted(path for path in SOURCE.glob("*.py") if path.name in CRITICAL_MODULES):
        executable = executable_lines(path)
        covered = {
            line
            for (filename, line), count in counts.items()
            if Path(filename) == path and count and line in executable
        }
        total_executable += len(executable)
        total_covered += len(covered)
        modules.append(
            {
                "module": path.name,
                "executable": len(executable),
                "covered": len(covered),
                "missing": sorted(executable - covered),
                "percent": round(100 * len(covered) / len(executable), 2) if executable else 100,
            }
        )

    percent = round(100 * total_covered / total_executable, 2)
    report = {
        "scope": sorted(CRITICAL_MODULES),
        "lineCoveragePercent": percent,
        "coveredStatements": total_covered,
        "executableStatements": total_executable,
        "modules": modules,
    }
    output = ROOT / "reports" / "coverage"
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if test_result.wasSuccessful() and percent >= 85 else 1


def run_tests() -> unittest.TestResult:
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    return unittest.TextTestRunner(verbosity=0).run(suite)


if __name__ == "__main__":
    raise SystemExit(main())
