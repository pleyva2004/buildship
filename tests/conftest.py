"""Shared pytest fixtures."""

import pytest


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    """Run each test in a temp cwd so trajectories/ and library JSON don't litter the repo.

    `pythonpath = ["."]` (pyproject) puts the repo root on sys.path as an absolute
    path at collection time, so `import buildship` still resolves after the chdir.
    """
    monkeypatch.chdir(tmp_path)
    yield
