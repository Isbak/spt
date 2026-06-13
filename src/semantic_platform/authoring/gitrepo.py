"""Thin git wrapper (over ``subprocess``) for domain content repositories.

Used by the authoring flow to write generated files into a sandboxed clone of a
*separate* domain repo on a feature branch, then surface them as a Pull Request for
human review. Pure-local operations (init/clone/branch/read/write/tree/commit) are
exercised offline in tests via ``file://`` remotes; network operations (push, PR
creation) degrade gracefully and are marked ``pragma: no cover``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import re
import subprocess

_GITHUB_SLUG_RE = re.compile(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$")


class GitError(RuntimeError):
    """Raised when a git command fails."""


@dataclass(frozen=True)
class PullRequestRef:
    """Outcome of a commit+push: the created PR or a fallback compare URL."""

    branch: str
    pushed: bool
    pull_request_url: str | None
    compare_url: str | None
    message: str


@dataclass(frozen=True)
class FileStatus:
    """Git status for one file: the raw porcelain codes plus a display badge."""

    path: str
    index: str  # staged-change code (porcelain column X), e.g. "A", "M", " "
    worktree: str  # worktree-change code (porcelain column Y), e.g. "M", "?", " "
    code: str  # single-letter display badge: "A"/"M"/"D"/"R"/"U"


@dataclass(frozen=True)
class WorkspaceStatus:
    """Working-tree status for a domain repository (branch + changed files)."""

    branch: str
    files: tuple[FileStatus, ...]
    clean: bool


def _run_allow_fail(args: list[str], cwd: Path | None = None) -> str:
    """Run a git command and return stdout regardless of exit code.

    Used for commands like ``git diff --no-index`` that intentionally exit
    non-zero when files differ — :func:`_run` would raise on that.
    """
    result = subprocess.run(  # noqa: S603 - args are constructed internally
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _run(args: list[str], cwd: Path | None = None) -> str:
    """Run a git command and return stdout, raising :class:`GitError` on failure."""
    result = subprocess.run(  # noqa: S603 - args are constructed internally
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise GitError(f"git {' '.join(args)} failed: {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout


class GitRepo:
    """A local working copy of a domain content repository."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    @property
    def exists(self) -> bool:
        """Return ``True`` when the path is an initialized git repository."""
        return (self.path / ".git").is_dir()

    def init(self) -> GitRepo:
        """Initialize an empty repository (with an initial empty commit)."""
        self.path.mkdir(parents=True, exist_ok=True)
        _run(["init", "-q"], cwd=self.path)
        self._ensure_identity()
        _run(["commit", "--allow-empty", "-q", "-m", "Initialize domain workspace"], cwd=self.path)
        return self

    def clone(self, remote_url: str) -> GitRepo:  # pragma: no cover - network/remote
        """Clone ``remote_url`` into the local path."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        _run(["clone", "-q", remote_url, str(self.path)])
        self._ensure_identity()
        return self

    @classmethod
    def clone_or_open(cls, local_path: Path | str, remote_url: str = "") -> GitRepo:
        """Open an existing local repo, else clone from ``remote_url``, else init."""
        repo = cls(local_path)
        if repo.exists:
            return repo
        if remote_url and not str(remote_url).startswith("https://github.com/your-"):
            try:  # pragma: no cover - network/remote
                return repo.clone(remote_url)
            except GitError:  # pragma: no cover - fall back to a local repo
                pass
        return repo.init()

    def _ensure_identity(self) -> None:
        """Set a local commit identity and disable signing for sandbox commits."""
        defaults = {
            "user.email": "authoring@semantic-platform.local",
            "user.name": "Semantic Platform Authoring",
        }
        for key, value in defaults.items():
            try:
                if not _run(["config", key], cwd=self.path).strip():
                    _run(["config", key, value], cwd=self.path)
            except GitError:
                _run(["config", key, value], cwd=self.path)
        # Sandbox commits are local review artifacts; never sign them.
        _run(["config", "commit.gpgsign", "false"], cwd=self.path)

    def checkout_branch(self, branch: str) -> GitRepo:
        """Create or switch to ``branch``."""
        existing = {line.strip().lstrip("* ").strip() for line in _run(["branch"], cwd=self.path).splitlines()}
        _run(["checkout", "-q", branch] if branch in existing else ["checkout", "-q", "-b", branch], cwd=self.path)
        return self

    def write_file(self, relative_path: str, content: str) -> Path:
        """Write ``content`` to a file relative to the repo root, creating dirs."""
        target = self.path / relative_path
        if not target.resolve().is_relative_to(self.path.resolve()):
            raise GitError(f"Refusing to write outside the repository: {relative_path}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def read_file(self, relative_path: str) -> str:
        """Return the text content of a file relative to the repo root."""
        target = self.path / relative_path
        if not target.resolve().is_relative_to(self.path.resolve()) or not target.is_file():
            raise GitError(f"No such file in repository: {relative_path}")
        return target.read_text(encoding="utf-8")

    def tree(self) -> list[str]:
        """Return all tracked/untracked file paths (relative), excluding ``.git``."""
        paths: list[str] = []
        for entry in sorted(self.path.rglob("*")):
            if entry.is_file() and ".git" not in entry.relative_to(self.path).parts:
                paths.append(str(entry.relative_to(self.path)).replace(os.sep, "/"))
        return paths

    def status(self) -> WorkspaceStatus:
        """Return the working-tree status (branch + changed files) via porcelain."""
        out = _run(["status", "--porcelain=v1", "--branch", "--untracked-files=all"], cwd=self.path)
        branch = ""
        files: list[FileStatus] = []
        for line in out.splitlines():
            if line.startswith("## "):
                branch = self._parse_branch(line[3:])
                continue
            if len(line) < 4:
                continue
            index, worktree, rest = line[0], line[1], line[3:]
            # Rename lines read "old -> new"; keep the new path.
            path = rest.split(" -> ", 1)[-1].strip()
            files.append(FileStatus(path=path, index=index, worktree=worktree,
                                    code=self._badge(index, worktree)))
        return WorkspaceStatus(branch=branch, files=tuple(files), clean=not files)

    @staticmethod
    def _parse_branch(header: str) -> str:
        """Extract the branch name from a porcelain ``## ...`` header line."""
        header = header.strip()
        if header.startswith("No commits yet on "):
            header = header[len("No commits yet on "):]
        return header.split("...", 1)[0].strip()

    @staticmethod
    def _badge(index: str, worktree: str) -> str:
        """Collapse the two porcelain status columns into one display badge."""
        if index == "?" or worktree == "?":
            return "U"
        change = worktree if worktree != " " else index
        return change if change != " " else "M"

    def diff(self, relative_path: str) -> str:
        """Return the unified diff for one file (``""`` when clean/unavailable)."""
        target = self.path / relative_path
        if not target.resolve().is_relative_to(self.path.resolve()):
            raise GitError(f"Refusing to diff outside the repository: {relative_path}")
        # Tracked files: a clean file yields an empty diff, a modified file a real one.
        if _run(["ls-files", "--", relative_path], cwd=self.path).strip():
            return _run(["diff", "--", relative_path], cwd=self.path)
        # Untracked files have no tracked diff; show them against /dev/null.
        # ``--no-index`` intentionally exits non-zero when files differ.
        if target.is_file():
            return _run_allow_fail(["diff", "--no-index", "--", os.devnull, relative_path],
                                   cwd=self.path)
        return ""

    def commit(self, message: str) -> str | None:
        """Stage all changes and commit; return the commit SHA or ``None`` if clean."""
        _run(["add", "-A"], cwd=self.path)
        if not _run(["status", "--porcelain"], cwd=self.path).strip():
            return None
        self._ensure_identity()
        _run(["commit", "-q", "-m", message], cwd=self.path)
        return _run(["rev-parse", "HEAD"], cwd=self.path).strip()

    def push(self, branch: str, token_env: str | None = None, remote: str = "origin") -> bool:
        """Push ``branch`` to ``remote``, injecting a token from ``token_env`` if set."""
        token = os.getenv(token_env) if token_env else None
        if token:  # pragma: no cover - requires an authenticated network remote
            url = _run(["remote", "get-url", remote], cwd=self.path).strip()
            authed = re.sub(r"https://", f"https://x-access-token:{token}@", url, count=1)
            _run(["push", authed, f"{branch}:{branch}"], cwd=self.path)
        else:
            _run(["push", "-u", remote, branch], cwd=self.path)
        return True


def github_compare_url(remote_url: str, branch: str, base: str) -> str | None:
    """Return a GitHub 'compare/open PR' URL for a remote, or ``None`` if not GitHub."""
    match = _GITHUB_SLUG_RE.search(remote_url or "")
    if not match:
        return None
    owner, repo = match.group("owner"), match.group("repo")
    return f"https://github.com/{owner}/{repo}/compare/{base}...{branch}?expand=1"


def open_pull_request(
    remote_url: str,
    branch: str,
    base: str,
    title: str,
    body: str,
    token_env: str | None = None,
) -> PullRequestRef:
    """Open a PR via the GitHub API when a token is available, else return a compare URL."""
    compare = github_compare_url(remote_url, branch, base)
    token = os.getenv(token_env) if token_env else None
    if not token or not compare:
        return PullRequestRef(
            branch=branch,
            pushed=False,
            pull_request_url=None,
            compare_url=compare,
            message="Branch ready for review. Open a PR using the compare link." if compare else "Branch committed locally.",
        )
    match = _GITHUB_SLUG_RE.search(remote_url)  # pragma: no cover - network
    owner, repo = match.group("owner"), match.group("repo")  # pragma: no cover - network
    import requests  # pragma: no cover - network

    response = requests.post(  # pragma: no cover - network
        f"https://api.github.com/repos/{owner}/{repo}/pulls",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        json={"title": title, "head": branch, "base": base, "body": body},
        timeout=15,
    )
    if response.status_code >= 300:  # pragma: no cover - network
        return PullRequestRef(branch, True, None, compare, f"Pushed; PR creation failed ({response.status_code}). Use the compare link.")
    url = response.json().get("html_url")  # pragma: no cover - network
    return PullRequestRef(branch, True, url, compare, "Pull request opened for review.")  # pragma: no cover - network
