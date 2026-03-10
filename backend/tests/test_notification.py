"""通知サービスのテスト"""

import uuid
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.models.alert import Alert, AlertSeverity, AlertType
from app.services.notification import NotificationService, NOTIFICATION_CONFIG


class TestNotificationConfig:
    """通知設定のテスト"""

    def test_all_severities_have_config(self):
        for severity in [AlertSeverity.INFO, AlertSeverity.WARNING, AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY]:
            assert severity in NOTIFICATION_CONFIG
            config = NOTIFICATION_CONFIG[severity]
            assert "sound" in config
            assert "priority" in config
            assert "channel_id" in config

    def test_critical_is_high_priority(self):
        assert NOTIFICATION_CONFIG[AlertSeverity.CRITICAL]["priority"] == "high"
        assert NOTIFICATION_CONFIG[AlertSeverity.EMERGENCY]["priority"] == "high"

    def test_info_is_normal_priority(self):
        assert NOTIFICATION_CONFIG[AlertSeverity.INFO]["priority"] == "normal"


class TestNotificationService:
    """NotificationServiceのテスト"""

    @pytest.mark.asyncio
    async def test_send_push_without_fcm_skips(self):
        """FCM未設定の場合は送信をスキップする"""
        service = NotificationService()
        result = await service.send_push(
            user_id=uuid.uuid4(),
            title="テスト",
            body="テスト通知",
            db=MagicMock(),
        )
        # FCM未初期化なのでFalseが返る
        assert result is False

    @pytest.mark.asyncio
    async def test_send_push_without_db_fails(self):
        """DBセッション未提供で失敗する"""
        service = NotificationService()
        result = await service.send_push(
            user_id=uuid.uuid4(),
            title="テスト",
            body="テスト通知",
            db=None,
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_send_alert_notification_builds_correct_title(self):
        """アラート通知のタイトルにプレフィックスが付く"""
        service = NotificationService()

        alert = MagicMock(spec=Alert)
        alert.id = uuid.uuid4()
        alert.alert_type = AlertType.ROUTE_DEVIATION
        alert.severity = AlertSeverity.WARNING
        alert.title = "ルート逸脱"
        alert.message = "通学路から外れています"
        alert.child_id = uuid.uuid4()
        alert.latitude = 35.68
        alert.longitude = 139.76

        with patch.object(service, "send_push", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            db = MagicMock()
            await service.send_alert_notification(
                user_id=uuid.uuid4(),
                alert=alert,
                db=db,
            )
            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args[1]
            assert "⚠️" in call_kwargs["title"]
            assert "ルート逸脱" in call_kwargs["title"]
            assert call_kwargs["data"]["alert_type"] == AlertType.ROUTE_DEVIATION

    @pytest.mark.asyncio
    async def test_send_escalation_notification(self):
        """エスカレーション通知が正しく構築される"""
        service = NotificationService()

        alert = MagicMock(spec=Alert)
        alert.id = uuid.uuid4()
        alert.severity = AlertSeverity.CRITICAL
        alert.title = "速度異常"
        alert.message = "異常な速度で移動中"

        with patch.object(service, "send_push", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            db = MagicMock()
            await service.send_escalation_notification(
                user_id=uuid.uuid4(),
                alert=alert,
                db=db,
            )
            call_kwargs = mock_send.call_args[1]
            assert "エスカレーション" in call_kwargs["title"]
            assert "重大" in call_kwargs["title"]
            assert call_kwargs["data"]["type"] == "escalation"

    @pytest.mark.asyncio
    async def test_send_arrival_notification(self):
        """到着通知が正しく送信される"""
        service = NotificationService()

        with patch.object(service, "send_push", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            db = MagicMock()
            await service.send_arrival_notification(
                user_id=uuid.uuid4(),
                child_name="太郎",
                destination_name="学校",
                db=db,
            )
            call_kwargs = mock_send.call_args[1]
            assert "到着" in call_kwargs["title"]
            assert "太郎" in call_kwargs["body"]
            assert "学校" in call_kwargs["body"]

    @pytest.mark.asyncio
    async def test_send_departure_notification(self):
        """出発通知が正しく送信される"""
        service = NotificationService()

        with patch.object(service, "send_push", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            db = MagicMock()
            await service.send_departure_notification(
                user_id=uuid.uuid4(),
                child_name="花子",
                origin_name="自宅",
                db=db,
            )
            call_kwargs = mock_send.call_args[1]
            assert "出発" in call_kwargs["title"]
            assert "花子" in call_kwargs["body"]
            assert "自宅" in call_kwargs["body"]
