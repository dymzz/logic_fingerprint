from __future__ import annotations

from pathlib import Path

from scripts.release_package import (
    build_parser,
    collect_distribution_files,
    ensure_python_module,
    is_distribution_file,
    resolve_repository_args,
)


def test_collect_distribution_files_returns_supported_artifacts(tmp_path: Path) -> None:
    wheel = tmp_path / "logicfp-2.0.0-py3-none-any.whl"
    sdist = tmp_path / "logicfp-2.0.0.tar.gz"
    ignored = tmp_path / "README.txt"
    wheel.write_text("wheel", encoding="utf-8")
    sdist.write_text("sdist", encoding="utf-8")
    ignored.write_text("ignored", encoding="utf-8")

    artifacts = collect_distribution_files(tmp_path)

    assert artifacts == [wheel, sdist]


def test_collect_distribution_files_requires_artifacts(tmp_path: Path) -> None:
    try:
        collect_distribution_files(tmp_path)
    except FileNotFoundError as exc:
        assert "No package artifacts found" in str(exc)
    else:
        raise AssertionError("Expected FileNotFoundError when dist directory is empty")


def test_is_distribution_file_recognizes_supported_suffixes(tmp_path: Path) -> None:
    wheel = tmp_path / "logicfp-2.0.0-py3-none-any.whl"
    sdist = tmp_path / "logicfp-2.0.0.tar.gz"
    text_file = tmp_path / "logicfp-2.0.0.txt"
    wheel.write_text("wheel", encoding="utf-8")
    sdist.write_text("sdist", encoding="utf-8")
    text_file.write_text("text", encoding="utf-8")

    assert is_distribution_file(wheel) is True
    assert is_distribution_file(sdist) is True
    assert is_distribution_file(text_file) is False


def test_release_parser_supports_publish_flag() -> None:
    args = build_parser().parse_args(["release", "--publish", "--repository", "pypi"])

    assert args.command == "release"
    assert args.publish is True
    assert args.repository == "pypi"


def test_publish_parser_supports_testpypi_flag() -> None:
    args = build_parser().parse_args(["publish", "--testpypi"])

    assert args.command == "publish"
    assert args.testpypi is True


def test_resolve_repository_args_prefers_testpypi_template() -> None:
    repository, repository_url = resolve_repository_args(
        repository="pypi",
        repository_url="https://upload.pypi.org/legacy/",
        testpypi=True,
    )

    assert repository == "testpypi"
    assert repository_url is None


def test_ensure_python_module_raises_helpful_error(monkeypatch) -> None:
    monkeypatch.setattr("importlib.util.find_spec", lambda name: None)

    try:
        ensure_python_module("build")
    except RuntimeError as exc:
        assert "pip install .[release]" in str(exc)
        assert "pip install build" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError when module is missing")
