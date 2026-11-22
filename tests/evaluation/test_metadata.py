"""Inject Git command results; container images intentionally contain no .git."""

import subprocess

from eval.run import source_metadata


def test_container_without_git_has_explicit_unknown_revision():
    def absent_git(args, **kwargs):
        raise FileNotFoundError("git")

    assert source_metadata(command=absent_git) == {
        "git_commit": None, "working_tree_dirty": None, "git_metadata_available": False,
    }


def test_non_checkout_has_explicit_unknown_revision():
    def not_a_repository(args, **kwargs):
        raise subprocess.CalledProcessError(128, args)

    assert source_metadata(command=not_a_repository)["git_metadata_available"] is False


def test_native_checkout_preserves_commit_and_clean_state():
    def clean_git(args, **kwargs):
        return "abc123\n" if args[1] == "rev-parse" else ""

    assert source_metadata(command=clean_git) == {
        "git_commit": "abc123", "working_tree_dirty": False, "git_metadata_available": True,
    }
