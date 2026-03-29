from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = REPO_ROOT / "dist"
BUILD_DIR = REPO_ROOT / "build"
PACKAGE_EXTENSIONS = (".whl", ".tar.gz")
TEST_PYPI_REPOSITORY = "testpypi"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="release_package.py",
        description="Build, validate, and publish the logicfp package.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="Build sdist and wheel.")
    build_parser.add_argument(
        "--keep-dist",
        action="store_true",
        help="Keep existing build/ and dist/ contents before building.",
    )

    check_parser = subparsers.add_parser("check", help="Run twine check on dist artifacts.")
    check_parser.add_argument(
        "--dist-dir",
        default=str(DIST_DIR),
        help="Directory containing built package artifacts.",
    )

    publish_parser = subparsers.add_parser("publish", help="Upload dist artifacts with twine.")
    publish_parser.add_argument(
        "--dist-dir",
        default=str(DIST_DIR),
        help="Directory containing built package artifacts.",
    )
    publish_parser.add_argument(
        "--repository",
        default=None,
        help="Twine repository name, for example pypi or testpypi.",
    )
    publish_parser.add_argument(
        "--repository-url",
        default=None,
        help="Explicit Twine repository URL.",
    )
    publish_parser.add_argument(
        "--testpypi",
        action="store_true",
        help="Use the built-in TestPyPI repository template.",
    )
    publish_parser.add_argument(
        "--skip-check",
        action="store_true",
        help="Upload directly without running twine check first.",
    )

    release_parser = subparsers.add_parser(
        "release",
        help="Build artifacts, run twine check, then optionally upload them.",
    )
    release_parser.add_argument(
        "--keep-dist",
        action="store_true",
        help="Keep existing build/ and dist/ contents before building.",
    )
    release_parser.add_argument(
        "--publish",
        action="store_true",
        help="Upload artifacts after build and check succeed.",
    )
    release_parser.add_argument(
        "--repository",
        default=None,
        help="Twine repository name, for example pypi or testpypi.",
    )
    release_parser.add_argument(
        "--repository-url",
        default=None,
        help="Explicit Twine repository URL.",
    )
    release_parser.add_argument(
        "--testpypi",
        action="store_true",
        help="Use the built-in TestPyPI repository template.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "build":
        build_package(keep_dist=args.keep_dist)
        return 0
    if args.command == "check":
        check_package(Path(args.dist_dir))
        return 0
    if args.command == "publish":
        repository, repository_url = resolve_repository_args(
            repository=args.repository,
            repository_url=args.repository_url,
            testpypi=args.testpypi,
        )
        publish_package(
            Path(args.dist_dir),
            repository=repository,
            repository_url=repository_url,
            skip_check=args.skip_check,
        )
        return 0
    if args.command == "release":
        build_package(keep_dist=args.keep_dist)
        check_package(DIST_DIR)
        if args.publish:
            repository, repository_url = resolve_repository_args(
                repository=args.repository,
                repository_url=args.repository_url,
                testpypi=args.testpypi,
            )
            publish_package(
                DIST_DIR,
                repository=repository,
                repository_url=repository_url,
                skip_check=True,
            )
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


def build_package(*, keep_dist: bool) -> None:
    if not keep_dist:
        clean_directory(BUILD_DIR)
        clean_directory(DIST_DIR)
    run_command([sys.executable, "-m", "build"], cwd=REPO_ROOT)


def check_package(dist_dir: Path) -> None:
    artifacts = collect_distribution_files(dist_dir)
    run_command([sys.executable, "-m", "twine", "check", *map(str, artifacts)], cwd=REPO_ROOT)


def publish_package(
    dist_dir: Path,
    *,
    repository: str | None,
    repository_url: str | None,
    skip_check: bool,
) -> None:
    artifacts = collect_distribution_files(dist_dir)
    if not skip_check:
        check_package(dist_dir)

    command = [sys.executable, "-m", "twine", "upload"]
    if repository:
        command.extend(["--repository", repository])
    if repository_url:
        command.extend(["--repository-url", repository_url])
    command.extend(map(str, artifacts))
    run_command(command, cwd=REPO_ROOT)


def resolve_repository_args(
    *,
    repository: str | None,
    repository_url: str | None,
    testpypi: bool,
) -> tuple[str | None, str | None]:
    if testpypi:
        return TEST_PYPI_REPOSITORY, None
    return repository, repository_url


def collect_distribution_files(dist_dir: Path) -> list[Path]:
    if not dist_dir.exists():
        raise FileNotFoundError(f"Distribution directory does not exist: {dist_dir}")

    artifacts = sorted(path for path in dist_dir.iterdir() if is_distribution_file(path))
    if not artifacts:
        raise FileNotFoundError(f"No package artifacts found in: {dist_dir}")
    return artifacts


def is_distribution_file(path: Path) -> bool:
    if not path.is_file():
        return False
    name = path.name
    return name.endswith(PACKAGE_EXTENSIONS)


def clean_directory(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def run_command(command: Sequence[str], *, cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


if __name__ == "__main__":
    raise SystemExit(main())
