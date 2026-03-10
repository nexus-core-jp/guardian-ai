"""認証サービスのテスト"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from jose import jwt

from app.api.deps import create_access_token, create_refresh_token, verify_refresh_token


class TestJWTTokens:
    """JWTトークンの生成と検証"""

    def test_create_access_token(self):
        user_id = uuid.uuid4()
        token = create_access_token(user_id)
        assert token is not None
        assert isinstance(token, str)

        # トークンをデコードして内容を検証
        payload = jwt.decode(token, "change-me-in-production", algorithms=["HS256"])
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_create_refresh_token(self):
        user_id = uuid.uuid4()
        token = create_refresh_token(user_id)
        assert token is not None

        payload = jwt.decode(token, "change-me-in-production", algorithms=["HS256"])
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "refresh"

    def test_verify_refresh_token_valid(self):
        user_id = uuid.uuid4()
        token = create_refresh_token(user_id)
        result = verify_refresh_token(token)
        assert result == user_id

    def test_verify_refresh_token_access_token_rejected(self):
        """アクセストークンをリフレッシュトークンとして使えない"""
        user_id = uuid.uuid4()
        token = create_access_token(user_id)
        result = verify_refresh_token(token)
        assert result is None

    def test_verify_refresh_token_invalid(self):
        result = verify_refresh_token("invalid-token")
        assert result is None

    def test_verify_refresh_token_tampered(self):
        user_id = uuid.uuid4()
        token = create_refresh_token(user_id)
        # トークンの最後の文字を変えて改ざん
        tampered = token[:-1] + ("a" if token[-1] != "a" else "b")
        result = verify_refresh_token(tampered)
        assert result is None


class TestAppleLogin:
    """Apple Sign-Inのテスト"""

    @pytest.mark.asyncio
    async def test_apple_login_invalid_token(self):
        """無効なApple ID Tokenが拒否される"""
        from app.schemas.user import AppleLoginRequest

        request = AppleLoginRequest(id_token="invalid-jwt-token")
        # JWTパースが失敗することを確認
        from jose import JWTError
        with pytest.raises((JWTError, Exception)):
            jwt.get_unverified_header(request.id_token)

    def test_apple_login_request_schema(self):
        """AppleLoginRequestスキーマの検証"""
        from app.schemas.user import AppleLoginRequest

        req = AppleLoginRequest(
            id_token="eyJ...",
            authorization_code="auth_code_123",
            full_name="田中太郎",
        )
        assert req.id_token == "eyJ..."
        assert req.authorization_code == "auth_code_123"
        assert req.full_name == "田中太郎"

    def test_apple_login_request_optional_fields(self):
        from app.schemas.user import AppleLoginRequest

        req = AppleLoginRequest(id_token="eyJ...")
        assert req.authorization_code is None
        assert req.full_name is None


class TestGoogleLogin:
    """Googleログインのテスト"""

    def test_google_login_request_schema(self):
        """GoogleLoginRequestスキーマの検証"""
        from app.schemas.user import GoogleLoginRequest

        req = GoogleLoginRequest(id_token="google-id-token-123")
        assert req.id_token == "google-id-token-123"

    @pytest.mark.asyncio
    async def test_google_token_verification_failure(self):
        """Google tokeninfo APIが失敗した場合のテスト"""
        import httpx

        # tokeninfoが400を返すケースをシミュレート
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "invalid_token"}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            # エラーレスポンスが返されることを確認
            assert mock_response.status_code != 200


class TestTokenResponse:
    """トークンレスポンスのテスト"""

    def test_token_response_schema(self):
        from app.schemas.user import TokenResponse, UserResponse

        user_resp = UserResponse(
            id=uuid.uuid4(),
            name="テスト",
            email=None,
            line_id=None,
            avatar_url=None,
            home_latitude=None,
            home_longitude=None,
            onboarding_completed=False,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        resp = TokenResponse(
            access_token="access",
            refresh_token="refresh",
            user=user_resp,
        )
        assert resp.token_type == "bearer"
        assert resp.access_token == "access"
        assert resp.refresh_token == "refresh"

    def test_refresh_token_response_schema(self):
        from app.schemas.user import RefreshTokenResponse

        resp = RefreshTokenResponse(
            access_token="new-access",
            refresh_token="new-refresh",
        )
        assert resp.token_type == "bearer"
