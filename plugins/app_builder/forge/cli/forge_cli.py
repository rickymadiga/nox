# forge/cli/forge_cli.py

import argparse
import sys
from pathlib import Path
from typing import Optional

# Extensions
from extensions.test_chain_with_fixer import run_full_chain


__version__ = "0.0.4"


# -----------------------------
# CLI Argument Parsing
# -----------------------------
def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="forge",
        description="Forge V10 – Autonomous Code Builder",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:

  forge build "Create a todo API"

  forge chain-test "Add two numbers" --code-file script.py

  echo 'print("Hello")' | forge chain-test "Simple print"

  forge chain-test "Inline test" --code 'print(42)'
"""
    )

    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # -----------------------------
    # BUILD COMMAND
    # -----------------------------
    build_parser = subparsers.add_parser(
        "build",
        help="Build project from description"
    )

    build_parser.add_argument(
        "description",
        type=str,
        help="Task description"
    )

    # -----------------------------
    # CHAIN TEST COMMAND
    # -----------------------------
    chain_parser = subparsers.add_parser(
        "chain-test",
        help="Run full agent chain (Executor → Evaluator → Fixer → Archive + Artifact)"
    )

    chain_parser.add_argument(
        "description",
        nargs="?",
        default="Test full agent chain",
        help="Task description (optional if code provided)"
    )

    chain_parser.add_argument(
        "--code-file",
        type=str,
        help="Path to Python file containing code"
    )

    chain_parser.add_argument(
        "--code",
        type=str,
        help="Inline Python snippet"
    )

    return parser.parse_args()


# -----------------------------
# CODE LOADING
# -----------------------------
def load_user_code(args: argparse.Namespace) -> Optional[str]:
    """
    Load code from highest priority source:

    1. --code-file
    2. --code inline
    3. stdin (pipe)
    4. None (chain fallback)
    """

    # -----------------------------
    # From file
    # -----------------------------
    if args.code_file:
        path = Path(args.code_file)

        if not path.exists():
            raise FileNotFoundError(f"Code file not found: {path}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {path}")

        return path.read_text(encoding="utf-8")

    # -----------------------------
    # Inline code
    # -----------------------------
    if args.code:
        return args.code

    # -----------------------------
    # From pipe (stdin)
    # -----------------------------
    if not sys.stdin.isatty():
        data = sys.stdin.read().strip()
        if data:
            return data

    return None


# -----------------------------
# CLI EXECUTION
# -----------------------------
def run_chain_test(args: argparse.Namespace) -> int:

    print("\n[Forge] Running full agent chain...\n")

    try:
        user_code = load_user_code(args)
    except Exception as e:
        print(f"[Forge Error] {e}")
        return 1

    # Preview code
    if user_code:
        preview = user_code[:300]
        if len(user_code) > 300:
            preview += "\n..."

        print("User code detected:\n")
        print(preview)
        print()

    else:
        print("No user code provided → using internal dummy example\n")

    # Run chain
    result = run_full_chain(
        task_description=args.description,
        dummy_code=user_code
    )

    # -----------------------------
    # Results
    # -----------------------------
    print("\nChain result summary:\n")

    for msg in result.get("messages", []):
        print(f"  • {msg}")

    if result.get("build_path"):
        print(f"\nFinal build artifact:")
        print(f"  {result['build_path']}")

    print(f"\nStatus: {result.get('status','unknown')}")

    return 0


def run_build(args: argparse.Namespace) -> int:
    print(f"\n[Forge v{__version__}] Build request\n")
    print(f"Description:")
    print(f"  {args.description}\n")

    print("(Build pipeline not implemented yet)")

    return 0


# -----------------------------
# MAIN ENTRY
# -----------------------------
def main() -> int:

    args = parse_arguments()

    if args.command == "build":
        return run_build(args)

    if args.command == "chain-test":
        return run_chain_test(args)

    print("Unknown command")
    return 1


if __name__ == "__main__":
    sys.exit(main())