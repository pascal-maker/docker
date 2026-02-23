"""Unit tests for GitHub OAuth code exchange."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from refactor_agent.auth.oauth import exchange_code_for_token


@pytest.mark.asyncio
async def test_exchange_code_for_token_success() -> None:
    """Valid code returns access token."""
    mock_response = (
        b'{"access_token":"gho_abc123","token_type":"bearer","scope":"read:user"}'
    )

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = mock_urlopen.return_value.__enter__.return_value
        mock_resp.status = 200
        mock_resp.read.return_value = mock_response

        token = await exchange_code_for_token(
            "valid_code",
            client_id="cid",
            client_secret="secret",
            redirect_uri="https://example.com/callback",
        )

    assert token == "gho_abc123"
    mock_urlopen.assert_called_once()


@pytest.mark.asyncio
async def test_exchange_code_for_token_empty_code_returns_none() -> None:
    """Empty code returns None without calling GitHub."""
    with patch("urllib.request.urlopen") as mock_urlopen:
        token = await exchange_code_for_token(
            "",
            client_id="cid",
            client_secret="secret",
            redirect_uri="https://example.com/callback",
        )

    assert token is None
    mock_urlopen.assert_not_called()


@pytest.mark.asyncio
async def test_exchange_code_for_token_missing_config_returns_none() -> None:
    """Missing client_id returns None without calling GitHub."""
    with patch("urllib.request.urlopen") as mock_urlopen:
        token = await exchange_code_for_token(
            "code",
            client_id="",
            client_secret="secret",
            redirect_uri="https://example.com/callback",
        )

    assert token is None
    mock_urlopen.assert_not_called()


@pytest.mark.asyncio
async def test_exchange_code_for_token_no_access_token_in_response() -> None:
    """Response without access_token returns None."""
    mock_response = b'{"error":"bad_verification_code"}'

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = mock_urlopen.return_value.__enter__.return_value
        mock_resp.status = 200
        mock_resp.read.return_value = mock_response

        token = await exchange_code_for_token(
            "bad_code",
            client_id="cid",
            client_secret="secret",
            redirect_uri="https://example.com/callback",
        )

    assert token is None
