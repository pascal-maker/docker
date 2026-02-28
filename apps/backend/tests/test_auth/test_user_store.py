"""Unit tests for UserStore with mocked Firestore."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from refactor_agent.auth.models import GitHubUser
from refactor_agent.auth.user_store import UserStore


def test_user_store_is_available_without_client() -> None:
    """UserStore with no client reports is_available False when project unset."""
    store = UserStore(client=None)
    assert store.is_available() is False


def test_user_store_is_available_with_client() -> None:
    """UserStore with mock client reports is_available True."""
    mock = MagicMock()
    store = UserStore(client=mock)
    assert store.is_available() is True


@pytest.mark.asyncio
async def test_get_or_create_user_alpha_creates_pending() -> None:
    """In alpha mode, new user gets status pending."""
    mock_doc = MagicMock()
    mock_doc.exists = False
    mock_doc_ref = MagicMock()
    mock_doc_ref.get.return_value = mock_doc
    mock_coll = MagicMock()
    mock_coll.document.return_value = mock_doc_ref
    mock_db = MagicMock()
    mock_db.collection.return_value = mock_coll

    store = UserStore(client=mock_db)
    github_user = GitHubUser(id=12345, login="alice", email="alice@example.com")

    record = await store.get_or_create_user(github_user, onboarding_mode="alpha")

    assert record.status == "pending"
    assert record.github_login == "alice"
    mock_doc_ref.set.assert_called_once()


@pytest.mark.asyncio
async def test_get_or_create_user_beta_creates_active() -> None:
    """In beta mode, new user gets status active."""
    mock_doc = MagicMock()
    mock_doc.exists = False
    mock_doc_ref = MagicMock()
    mock_doc_ref.get.return_value = mock_doc
    mock_coll = MagicMock()
    mock_coll.document.return_value = mock_doc_ref
    mock_db = MagicMock()
    mock_db.collection.return_value = mock_coll

    store = UserStore(client=mock_db)
    github_user = GitHubUser(id=12345, login="bob", email=None)

    record = await store.get_or_create_user(github_user, onboarding_mode="beta")

    assert record.status == "active"
    assert record.github_login == "bob"
