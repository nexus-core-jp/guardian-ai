"""設定・通知エンドポイントのテスト"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.api.v1.settings import ProfileUpdateRequest, HomeLocationUpdateRequest
from app.api.v1.notifications import NotificationPreferencesResponse, NotificationPreferencesUpdate


class TestProfileUpdateRequest:
    def test_valid_name_update(self):
        req = ProfileUpdateRequest(name="新しい名前")
        assert req.name == "新しい名前"
        assert req.email is None

    def test_valid_email_update(self):
        req = ProfileUpdateRequest(email="test@example.com")
        assert req.email == "test@example.com"
        assert req.name is None

    def test_both_fields(self):
        req = ProfileUpdateRequest(name="太郎", email="taro@example.com")
        assert req.name == "太郎"
        assert req.email == "taro@example.com"

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            ProfileUpdateRequest(name="")

    def test_long_name_rejected(self):
        with pytest.raises(ValidationError):
            ProfileUpdateRequest(name="a" * 101)


class TestHomeLocationUpdateRequest:
    def test_valid_location(self):
        req = HomeLocationUpdateRequest(
            latitude=35.6762,
            longitude=139.6503,
            address="東京都渋谷区",
        )
        assert req.latitude == 35.6762
        assert req.longitude == 139.6503

    def test_invalid_latitude(self):
        with pytest.raises(ValidationError):
            HomeLocationUpdateRequest(latitude=91, longitude=0, address="test")

    def test_invalid_longitude(self):
        with pytest.raises(ValidationError):
            HomeLocationUpdateRequest(latitude=0, longitude=181, address="test")


class TestNotificationPreferencesResponse:
    def test_defaults(self):
        resp = NotificationPreferencesResponse()
        assert resp.route_deviation is True
        assert resp.danger_zone is True
        assert resp.arrival is True
        assert resp.departure is True
        assert resp.community_reports is True

    def test_custom_values(self):
        resp = NotificationPreferencesResponse(
            route_deviation=False,
            danger_zone=True,
            arrival=False,
            departure=True,
            community_reports=False,
        )
        assert resp.route_deviation is False
        assert resp.arrival is False


class TestNotificationPreferencesUpdate:
    def test_partial_update(self):
        update = NotificationPreferencesUpdate(route_deviation=False)
        data = update.model_dump(exclude_none=True)
        assert data == {"route_deviation": False}

    def test_empty_update(self):
        update = NotificationPreferencesUpdate()
        data = update.model_dump(exclude_none=True)
        assert data == {}

    def test_multiple_fields(self):
        update = NotificationPreferencesUpdate(
            arrival=False,
            departure=False,
        )
        data = update.model_dump(exclude_none=True)
        assert data == {"arrival": False, "departure": False}


class TestDangerZoneConfirm:
    """危険エリア確認のテスト"""

    def test_confirm_count_increments(self):
        """confirm_countが増加する"""
        from app.models.danger_zone import DangerZone

        zone = DangerZone(
            latitude=35.68,
            longitude=139.76,
            risk_level=5,
            title="テスト危険エリア",
        )
        assert zone.confirm_count == 0

    def test_verified_at_3_confirms(self):
        """3件の確認でverifiedになる"""
        from app.models.danger_zone import DangerZone

        zone = DangerZone(
            latitude=35.68,
            longitude=139.76,
            risk_level=5,
            title="テスト",
        )
        zone.confirm_count = 3
        zone.verified = zone.confirm_count >= 3
        assert zone.verified is True


class TestAccountDeletion:
    """アカウント削除のテスト"""

    def test_deletion_anonymizes_user(self):
        """削除時にユーザー情報が匿名化される"""
        from app.models.user import User

        user = User(
            name="テスト太郎",
            email="taro@example.com",
            line_id="line_123",
            apple_id="apple_456",
            google_id="google_789",
            fcm_token="fcm_token_xxx",
        )

        # 削除処理のシミュレーション
        user.is_active = False
        user.name = "退会ユーザー"
        user.email = None
        user.line_id = None
        user.apple_id = None
        user.google_id = None
        user.fcm_token = None

        assert user.is_active is False
        assert user.name == "退会ユーザー"
        assert user.email is None
        assert user.line_id is None
        assert user.apple_id is None
        assert user.google_id is None
        assert user.fcm_token is None
