#!/usr/bin/env python3
"""
generate_tests.py — Coverage-driven test generation using Ollama.

Runs pytest with XML coverage, identifies uncovered lines per source file,
then calls an Ollama model (default: qwen2.5-coder) to generate new tests
that target those gaps. Writes output as behaviour-centric test files under
tests/unit/ following the project's naming and size conventions.

Usage (from repo root):
    python scripts/generate_tests.py [options]

Examples:
    # Basic run against all uncovered source files
    python scripts/generate_tests.py

    # Target a single module, dry-run
    python scripts/generate_tests.py --module sigenergy2mqtt/config.py --dry-run

    # Use a different Ollama host / model
    python scripts/generate_tests.py --ollama-url http://192.168.1.50:11434 --model qwen2.5-coder:32b

    # Only process files below a coverage threshold
    python scripts/generate_tests.py --min-uncovered 5
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import subprocess
import sys
import textwrap
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Configuration defaults
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = REPO_ROOT / "sigenergy2mqtt"
TESTS_DIR = REPO_ROOT / "tests"
UNIT_DIR = TESTS_DIR / "unit"
COVERAGE_XML = REPO_ROOT / "coverage.xml"

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5-coder"

# Soft / hard line limits from the project README
FILE_SOFT_LIMIT = 400
FILE_HARD_LIMIT = 700

# How many uncovered lines must exist before we bother generating tests
DEFAULT_MIN_UNCOVERED = 3

# Ollama generation parameters
OLLAMA_OPTIONS = {
    "temperature": 0.2,  # Low temp → deterministic, less hallucination
    "num_predict": 4096,
    "top_p": 0.9,
}

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class FileCoverage:
    """Coverage data for a single source file."""

    source_path: Path
    uncovered_lines: list[int] = field(default_factory=list)
    covered_lines: list[int] = field(default_factory=list)

    @property
    def total_lines(self) -> int:
        return len(self.covered_lines) + len(self.uncovered_lines)

    @property
    def coverage_pct(self) -> float:
        if self.total_lines == 0:
            return 100.0
        return 100.0 * len(self.covered_lines) / self.total_lines

    @property
    def module_name(self) -> str:
        """Dotted module name relative to SOURCE_DIR parent."""
        try:
            rel = self.source_path.relative_to(REPO_ROOT)
        except ValueError:
            rel = self.source_path
        return str(rel).replace("/", ".").removesuffix(".py")


@dataclass
class GenerationResult:
    file_coverage: FileCoverage
    output_path: Optional[Path]
    test_code: str
    skipped: bool = False
    skip_reason: str = ""


# ---------------------------------------------------------------------------
# Step 1 — Run pytest and produce coverage.xml
# ---------------------------------------------------------------------------


def run_pytest_coverage(
    pytest_args: list[str],
    xml_path: Path,
    cov_target: Optional[str] = None,
    test_paths: Optional[list[Path]] = None,
) -> bool:
    """
    Run pytest with --cov to produce an XML coverage report.

    Args:
        pytest_args:  Extra args forwarded verbatim to pytest.
        xml_path:     Where to write coverage.xml.
        cov_target:   Dotted module or package path for --cov (e.g.
                      "sigenergy2mqtt.config").  Defaults to the whole package.
        test_paths:   Explicit test files/dirs to run.  When supplied these
                      replace the default (run everything) so only the relevant
                      tests are executed.  Ignored when pytest_args already
                      contains positional paths.
    """
    effective_cov = cov_target or SOURCE_DIR.name

    # Build the test-path portion of the command.  If the caller already
    # passed positional paths via --pytest-args we leave those alone;
    # otherwise we use the auto-discovered test_paths (if any).
    extra_paths: list[str] = []
    if test_paths and not _pytest_args_contain_paths(pytest_args):
        extra_paths = [str(p) for p in test_paths]
        logging.info(
            "  Scoping test run to: %s",
            ", ".join(str(p.relative_to(REPO_ROOT)) for p in test_paths),
        )

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        f"--cov={effective_cov}",
        "--cov-branch",
        f"--cov-report=xml:{xml_path}",
        "--cov-report=term-missing:skip-covered",
        "-n",
        "auto",  # parallelise across available CPU cores
        "-q",
        "--tb=no",  # suppress tracebacks — we only want coverage data
        *extra_paths,
        *pytest_args,
    ]
    logging.info("Running: %s", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, cwd=REPO_ROOT)
    if not xml_path.exists():
        logging.error("coverage.xml was not produced — check pytest-cov is installed.")
        return False
    return True


def _pytest_args_contain_paths(pytest_args: list[str]) -> bool:
    """Return True if pytest_args already contains at least one path argument."""
    for arg in pytest_args:
        if not arg.startswith("-") and Path(arg).exists():
            return True
    return False


def module_path_to_cov_target(source_path: Path) -> str:
    """
    Convert an absolute source file path to the dotted --cov argument.

    e.g. /repo/sigenergy2mqtt/devices/foo.py → "sigenergy2mqtt.devices.foo"
    """
    rel = source_path.relative_to(REPO_ROOT)
    return str(rel).replace("/", ".").removesuffix(".py")


# ---------------------------------------------------------------------------
# Step 2 — Parse coverage.xml
# ---------------------------------------------------------------------------


def parse_coverage_xml(xml_path: Path, min_uncovered: int) -> list[FileCoverage]:
    """
    Parse a Cobertura-format coverage.xml and return one FileCoverage per
    source file that has >= min_uncovered uncovered lines.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    results: list[FileCoverage] = []

    for cls in root.iter("class"):
        filename = cls.get("filename", "")
        src_path = REPO_ROOT / filename
        if not src_path.exists():
            continue

        # Only care about our source package, not tests themselves
        try:
            src_path.relative_to(SOURCE_DIR)
        except ValueError:
            continue

        covered: list[int] = []
        uncovered: list[int] = []

        for line in cls.iter("line"):
            lineno = int(line.get("number", 0))
            hits = int(line.get("hits", 0))
            if hits > 0:
                covered.append(lineno)
            else:
                uncovered.append(lineno)

        if len(uncovered) >= min_uncovered:
            results.append(
                FileCoverage(
                    source_path=src_path,
                    covered_lines=sorted(covered),
                    uncovered_lines=sorted(uncovered),
                )
            )

    results.sort(key=lambda fc: fc.coverage_pct)  # worst coverage first
    return results


# ---------------------------------------------------------------------------
# Step 3 — Locate existing tests for a module
# ---------------------------------------------------------------------------


def find_existing_tests(fc: FileCoverage) -> list[Path]:
    """
    Find all existing test files that appear to test this source module.
    Heuristic: filename contains the source file's stem.
    """
    stem = fc.source_path.stem  # e.g. "config" from "config.py"
    matches: list[Path] = []
    for test_file in TESTS_DIR.rglob("test_*.py"):
        if stem in test_file.name:
            matches.append(test_file)
    return sorted(matches)


def read_file_excerpt(path: Path, max_lines: int = 600) -> str:
    """Read a file, truncating with a notice if it exceeds max_lines."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) <= max_lines:
        return "\n".join(lines)
    half = max_lines // 2
    truncated = lines[:half] + [f"\n... [{len(lines) - max_lines} lines omitted for brevity] ...\n"] + lines[-half:]
    return "\n".join(truncated)


def extract_uncovered_context(fc: FileCoverage, context: int = 3) -> str:
    """
    Return a condensed view of just the uncovered lines with surrounding
    context, numbered, to help the model focus its attention.
    """
    source_lines = fc.source_path.read_text(encoding="utf-8").splitlines()
    total = len(source_lines)
    uncovered_set = set(fc.uncovered_lines)

    # Build ranges of lines to show (uncovered ± context)
    to_show: set[int] = set()
    for ln in fc.uncovered_lines:
        for offset in range(-context, context + 1):
            idx = ln + offset
            if 1 <= idx <= total:
                to_show.add(idx)

    output_lines: list[str] = []
    prev_shown: Optional[int] = None
    for lineno in sorted(to_show):
        if prev_shown is not None and lineno > prev_shown + 1:
            output_lines.append("    ...")
        marker = ">>>" if lineno in uncovered_set else "   "
        output_lines.append(f"{marker} {lineno:4d}  {source_lines[lineno - 1]}")
        prev_shown = lineno

    return "\n".join(output_lines)


# ---------------------------------------------------------------------------
# Step 4 — Build the Ollama prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = textwrap.dedent("""\
    You are an expert Python test engineer specialising in pytest.

    Your task is to write **new pytest test functions** (and any necessary
    fixtures or imports) that cover the uncovered lines identified in the
    source code provided.

    Rules:
    - Output ONLY valid Python code. No markdown fences, no explanation.
    - Do NOT reproduce existing test functions verbatim; supplement them.
    - Each new test function name must start with `test_` and have a
      behaviour-centric name (e.g. `test_config_raises_on_missing_key`).
    - Use `pytest.raises`, `unittest.mock.patch`, `MagicMock`, or async
      equivalents as appropriate.
    - If the source uses `asyncio`, use `@pytest.mark.asyncio` and `async def`.
    - CRITICAL: always use the EXACT import path provided in the user message
      under "Correct import path". NEVER use placeholder names like
      `your_module`, `module`, or `source`. NEVER guess the import path.
    - Add a brief docstring to each test explaining what behaviour it verifies.
    - Do NOT add a `if __name__ == "__main__"` block.
    - Respect the existing conftest fixtures where they are referenced in
      existing tests.
    - Keep each test function focused and independent (no shared mutable state).
    - Aim to cover every `>>>` marked line at least once.
""")


def build_user_prompt(
    fc: FileCoverage,
    existing_tests: list[Path],
) -> str:
    parts: list[str] = []

    # Derive the importable module path and the public names it exports
    module_import = fc.module_name  # e.g. "sigenergy2mqtt.devices.foo"
    parts.append(f"## Correct import path: `{module_import}`")
    parts.append(f"All imports from the source file MUST use exactly: `from {module_import} import ...`  Do NOT use any other module name.")
    parts.append("")
    parts.append(f"## Source file: {fc.source_path.relative_to(REPO_ROOT)}")
    parts.append(f"## Coverage: {fc.coverage_pct:.1f}% ({len(fc.uncovered_lines)} uncovered lines of {fc.total_lines})")
    parts.append("")
    parts.append("### Uncovered lines (>>> marks the lines needing tests):")
    parts.append("")
    parts.append(extract_uncovered_context(fc))
    parts.append("")
    parts.append("### Full source file:")
    parts.append("")
    parts.append(read_file_excerpt(fc.source_path, max_lines=500))
    parts.append("")

    if existing_tests:
        parts.append("### Existing test files (do NOT duplicate these tests):")
        for tf in existing_tests[:3]:  # cap to avoid huge prompts
            parts.append(f"\n#### {tf.relative_to(REPO_ROOT)}")
            parts.append(read_file_excerpt(tf, max_lines=300))
    else:
        parts.append("### No existing tests found for this module.")

    parts.append("")
    parts.append("Now write only new pytest test functions (with necessary imports) that cover the uncovered lines marked with >>>. Output raw Python only — no markdown, no preamble.")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Step 5 — Call Ollama
# ---------------------------------------------------------------------------


def call_ollama(
    user_prompt: str,
    ollama_url: str,
    model: str,
    timeout: int = 300,
) -> str:
    """Call the Ollama /api/chat endpoint and return the assistant's reply."""
    payload = {
        "model": model,
        "stream": False,
        "options": OLLAMA_OPTIONS,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    }
    url = f"{ollama_url.rstrip('/')}/api/chat"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    body: dict = {}
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read())
            return body["message"]["content"]
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Ollama request failed: {exc}") from exc
    except KeyError as exc:
        raise RuntimeError(f"Unexpected Ollama response shape: {body!r}") from exc


# ---------------------------------------------------------------------------
# Step 6 — Sanitise model output
# ---------------------------------------------------------------------------


def sanitise_output(raw: str) -> str:
    """
    Strip markdown code fences the model sometimes adds despite instructions.
    """
    # Remove ```python ... ``` or ``` ... ``` wrappers
    raw = re.sub(r"^```(?:python)?\s*\n", "", raw.strip(), flags=re.MULTILINE)
    raw = re.sub(r"\n```\s*$", "", raw.strip(), flags=re.MULTILINE)
    return raw.strip()


# ---------------------------------------------------------------------------
# Step 7 — Decide output path
# ---------------------------------------------------------------------------


def infer_behavior_label(fc: FileCoverage, uncovered: list[int]) -> str:
    """
    Produce a short behaviour label for the new test file name by scanning
    function/class names near uncovered lines.
    """
    source_lines = fc.source_path.read_text(encoding="utf-8").splitlines()
    identifiers: list[str] = []

    for lineno in uncovered:
        # Walk backwards from the uncovered line to find the enclosing def/class
        for idx in range(lineno - 1, max(0, lineno - 30), -1):
            line = source_lines[idx]
            m = re.match(r"\s*(?:async\s+)?def\s+(\w+)\s*\(", line)
            if m:
                name = m.group(1)
                if name not in ("__init__", "__repr__", "__str__"):
                    identifiers.append(name)
                break
            m = re.match(r"\s*class\s+(\w+)\s*[:(]", line)
            if m:
                identifiers.append(m.group(1).lower())
                break

    if not identifiers:
        return "uncovered_paths"

    # Use the most frequent identifier as the label
    from collections import Counter

    most_common = Counter(identifiers).most_common(1)[0][0]
    # Convert CamelCase to snake_case
    label = re.sub(r"(?<!^)(?=[A-Z])", "_", most_common).lower()
    return label[:40]  # cap length


def determine_output_path(fc: FileCoverage, existing_tests: list[Path]) -> Path:
    """
    Determine where to write the new test file.

    Strategy:
    1. Find the unit/ subdirectory that matches the source module's package.
    2. Generate a behaviour-centric filename.
    3. Avoid colliding with existing filenames.
    """
    stem = fc.source_path.stem  # e.g. "config"

    # Find the corresponding unit subdirectory
    try:
        pkg_rel = fc.source_path.parent.relative_to(SOURCE_DIR)
        # e.g. sigenergy2mqtt/devices/foo.py → unit/devices/
        unit_subdir = UNIT_DIR / pkg_rel
    except ValueError:
        unit_subdir = UNIT_DIR

    unit_subdir.mkdir(parents=True, exist_ok=True)

    behavior = infer_behavior_label(fc, fc.uncovered_lines)
    candidate = unit_subdir / f"test_{stem}_{behavior}.py"

    # If the candidate already exists, append a counter suffix
    counter = 1
    while candidate.exists():
        candidate = unit_subdir / f"test_{stem}_{behavior}_{counter}.py"
        counter += 1

    return candidate


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------


def process_file(
    fc: FileCoverage,
    ollama_url: str,
    model: str,
    dry_run: bool,
    timeout: int,
) -> GenerationResult:
    existing_tests = find_existing_tests(fc)
    output_path = determine_output_path(fc, existing_tests)

    logging.info(
        "  Source:   %s  (%.1f%% covered, %d uncovered lines)",
        fc.source_path.relative_to(REPO_ROOT),
        fc.coverage_pct,
        len(fc.uncovered_lines),
    )
    logging.info("  Existing: %s", [str(t.relative_to(REPO_ROOT)) for t in existing_tests] or "none")
    logging.info("  Output:   %s", output_path.relative_to(REPO_ROOT))

    prompt = build_user_prompt(fc, existing_tests)

    logging.info("  Calling Ollama (%s)…", model)
    t0 = time.monotonic()
    try:
        raw = call_ollama(prompt, ollama_url, model, timeout=timeout)
    except RuntimeError as exc:
        logging.error("  Ollama call failed: %s", exc)
        return GenerationResult(
            file_coverage=fc,
            output_path=None,
            test_code="",
            skipped=True,
            skip_reason=str(exc),
        )
    elapsed = time.monotonic() - t0
    logging.info("  Ollama responded in %.1fs", elapsed)

    test_code = sanitise_output(raw)

    if not dry_run:
        output_path.write_text(test_code + "\n", encoding="utf-8")
        logging.info("  Written → %s", output_path.relative_to(REPO_ROOT))
    else:
        logging.info("  [dry-run] Would write %d chars to %s", len(test_code), output_path.relative_to(REPO_ROOT))

    return GenerationResult(
        file_coverage=fc,
        output_path=output_path,
        test_code=test_code,
    )


def print_summary(results: list[GenerationResult]) -> None:
    print("\n" + "=" * 72)
    print("SUMMARY")
    print("=" * 72)
    written = [r for r in results if not r.skipped and r.output_path]
    skipped = [r for r in results if r.skipped]
    print(f"  Generated: {len(written)} test file(s)")
    print(f"  Skipped:   {len(skipped)}")
    if written:
        print("\nGenerated files:")
        for r in written:
            assert r.output_path is not None
            print(f"  {r.output_path.relative_to(REPO_ROOT)}  ← {r.file_coverage.source_path.relative_to(REPO_ROOT)}  ({len(r.file_coverage.uncovered_lines)} uncovered lines)")
    if skipped:
        print("\nSkipped:")
        for r in skipped:
            print(f"  {r.file_coverage.source_path.relative_to(REPO_ROOT)}  — {r.skip_reason}")
    print()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--ollama-url",
        default=DEFAULT_OLLAMA_URL,
        help=f"Base URL of the Ollama server (default: {DEFAULT_OLLAMA_URL})",
    )
    p.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Ollama model name (default: {DEFAULT_MODEL})",
    )
    p.add_argument(
        "--module",
        metavar="PATH",
        help="Restrict generation to this source file only (e.g. sigenergy2mqtt/config.py)",
    )
    p.add_argument(
        "--min-uncovered",
        type=int,
        default=DEFAULT_MIN_UNCOVERED,
        help=f"Skip files with fewer than N uncovered lines (default: {DEFAULT_MIN_UNCOVERED})",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse coverage and build prompts but do not write any files or call Ollama",
    )
    p.add_argument(
        "--no-run-pytest",
        action="store_true",
        help="Skip running pytest; reuse an existing coverage.xml",
    )
    p.add_argument(
        "--pytest-args",
        nargs=argparse.REMAINDER,
        default=[],
        help="Extra arguments forwarded to pytest (e.g. -- tests/unit/config/)",
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="HTTP timeout for each Ollama call in seconds (default: 300)",
    )
    p.add_argument(
        "--max-files",
        type=int,
        default=0,
        help="Stop after generating tests for N files (0 = unlimited)",
    )
    p.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable DEBUG logging",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(message)s",
        datefmt="%H:%M:%S",
    )

    # ── Step 1: run pytest coverage ──────────────────────────────────────────
    if not args.no_run_pytest:
        cov_target: Optional[str] = None
        test_paths: Optional[list[Path]] = None

        if args.module:
            module_path = Path(args.module).resolve()
            cov_target = module_path_to_cov_target(module_path)
            # Auto-discover existing tests so we only run those
            dummy_fc = FileCoverage(source_path=module_path)
            discovered = find_existing_tests(dummy_fc)
            if discovered:
                test_paths = discovered
                logging.info(
                    "--module specified: scoping coverage to '%s', running %d matching test file(s).",
                    cov_target,
                    len(discovered),
                )
            else:
                logging.info(
                    "--module specified: scoping coverage to '%s'; no existing tests found — running full suite for baseline.",
                    cov_target,
                )

        logging.info("Running pytest with coverage…")
        run_pytest_coverage(args.pytest_args, COVERAGE_XML, cov_target=cov_target, test_paths=test_paths)
    else:
        logging.info("Skipping pytest run; using existing %s", COVERAGE_XML)

    if not COVERAGE_XML.exists():
        logging.error("coverage.xml not found at %s — aborting.", COVERAGE_XML)
        return 1

    # ── Step 2: parse coverage ────────────────────────────────────────────────
    file_coverages = parse_coverage_xml(COVERAGE_XML, args.min_uncovered)
    logging.info("Found %d source file(s) with ≥%d uncovered lines.", len(file_coverages), args.min_uncovered)

    # Apply --module filter
    if args.module:
        target = Path(args.module).resolve()
        file_coverages = [fc for fc in file_coverages if fc.source_path == target]
        if not file_coverages:
            logging.error("Module %s not found in coverage data or has no uncovered lines.", args.module)
            return 1

    if not file_coverages:
        logging.info("No files to process — coverage is already sufficient.")
        return 0

    # ── Step 3 … 6: generate tests ───────────────────────────────────────────
    if args.dry_run:
        logging.info("Dry-run mode: Ollama will NOT be called.")

    results: list[GenerationResult] = []
    for i, fc in enumerate(file_coverages):
        if args.max_files and i >= args.max_files:
            logging.info("Reached --max-files %d limit; stopping.", args.max_files)
            break

        logging.info(
            "\n[%d/%d] %s",
            i + 1,
            len(file_coverages) if not args.max_files else min(args.max_files, len(file_coverages)),
            fc.source_path.relative_to(REPO_ROOT),
        )

        if args.dry_run:
            prompt = build_user_prompt(fc, find_existing_tests(fc))
            out_path = determine_output_path(fc, find_existing_tests(fc))
            logging.info("  Would write: %s", out_path.relative_to(REPO_ROOT))
            logging.debug("  Prompt length: %d chars", len(prompt))
            results.append(GenerationResult(fc, out_path, "", skipped=False))
            continue

        result = process_file(
            fc,
            ollama_url=args.ollama_url,
            model=args.model,
            dry_run=False,
            timeout=args.timeout,
        )
        results.append(result)

    print_summary(results)
    return 0


if __name__ == "__main__":
    sys.exit(main())
