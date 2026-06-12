"""Tests for the git wrapper (offline, via local file:// remotes)."""

from __future__ import annotations

import subprocess

import pytest

from semantic_platform.authoring.gitrepo import (
    GitError,
    GitRepo,
    github_compare_url,
    open_pull_request,
)


def test_init_write_tree_read_commit(tmp_path):
    repo = GitRepo(tmp_path / "repo").init()
    assert repo.exists
    repo.checkout_branch("authoring/test")
    repo.write_file("rdf/ontology/ontology.ttl", "# hello\n")
    repo.write_file("rdf/data/sample.ttl", "# data\n")
    assert repo.tree() == ["rdf/data/sample.ttl", "rdf/ontology/ontology.ttl"]
    assert repo.read_file("rdf/ontology/ontology.ttl") == "# hello\n"
    sha = repo.commit("add files")
    assert sha
    # Nothing to commit the second time.
    assert repo.commit("noop") is None


def test_clone_or_open_opens_existing(tmp_path):
    path = tmp_path / "repo"
    GitRepo(path).init()
    reopened = GitRepo.clone_or_open(path, "")
    assert reopened.exists


def test_clone_or_open_from_file_remote(tmp_path):
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "-q", str(origin)], check=True)
    seed = GitRepo(tmp_path / "seed").init()
    subprocess.run(["git", "remote", "add", "origin", origin.as_uri()], cwd=seed.path, check=True)
    subprocess.run(["git", "push", "-q", "origin", "HEAD:main"], cwd=seed.path, check=True)

    cloned = GitRepo.clone_or_open(tmp_path / "work", origin.as_uri())
    assert cloned.exists


def test_push_to_file_remote(tmp_path):
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "-q", str(origin)], check=True)
    repo = GitRepo.clone_or_open(tmp_path / "work", origin.as_uri())
    repo.checkout_branch("authoring/x")
    repo.write_file("rdf/a.ttl", "# a\n")
    repo.commit("add a")
    assert repo.push("authoring/x") is True
    refs = subprocess.run(["git", "ls-remote", str(origin), "refs/heads/authoring/x"], capture_output=True, text=True).stdout
    assert "authoring/x" in refs


def test_write_outside_repo_is_refused(tmp_path):
    repo = GitRepo(tmp_path / "repo").init()
    with pytest.raises(GitError):
        repo.write_file("../escape.ttl", "x")
    with pytest.raises(GitError):
        repo.read_file("does/not/exist.ttl")


def test_run_raises_on_failure(tmp_path):
    with pytest.raises(GitError):
        GitRepo(tmp_path / "nope").read_file("a")  # no repo -> read fails


def test_compare_url_and_pr_fallback():
    assert github_compare_url("git@github.com:owner/repo.git", "feat", "main") == (
        "https://github.com/owner/repo/compare/main...feat?expand=1"
    )
    assert github_compare_url("https://gitlab.com/o/r.git", "feat", "main") is None

    ref = open_pull_request("https://github.com/owner/repo.git", "feat", "main", "t", "b", token_env=None)
    assert ref.pull_request_url is None
    assert ref.compare_url.endswith("compare/main...feat?expand=1")
    assert ref.pushed is False
