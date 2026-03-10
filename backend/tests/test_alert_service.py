"""アラートサービスのユニットテスト"""

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.alert_service import AlertService, ESCALATION_RULES
from app.services.anomaly_detector import AnomalyResult
from app.models.alert import Alert, AlertType, AlertSeverity


class TestCreateAlert:
    """アラート作成のテスト"""

    @pytest.fixture(autouse=True)
    def setup(self, mock_db, sample_user, sample_child):
        self.db = mock_db
        self.user = sample_user
        self.child = sample_child

        # NotificationServiceをモック
        with patch("app.services.alert_service.NotificationService") as mock_notif:
            mock_notif.return_value.send_alert_notification = AsyncMock(return_value=True)
            self.service = AlertService(self.db)
            self.service.notification_service = mock_notif.return_value

    @pytest.mark.asyncio
    async def test_create_new_alert(self):
        """新規アラートの作成"""
        # 既存アラートなし
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.db.execute.return_value = mock_result

        alert = await self.service.create_alert(
            child_id=self.child.id,
            user_id=self.user.id,
            alert_type=AlertType.SPEED_ANOMALY,
            severity=AlertSeverity.WARNING,
            title="速度異常",
            message="テストメッセージ",
            latitude=35.68,
            longitude=139.77,
        )

        assert alert is not None
        self.db.add.assert_called_once()
        self.db.flush.assert_called()

    @pytest.mark.asyncio
    async def test_duplicate_alert_suppressed(self):
        """5分以内の重複アラートは抑制される"""
        existing_alert = Alert(
            id=uuid.uuid4(),
            child_id=self.child.id,
            user_id=self.user.id,
            alert_type=AlertType.SPEED_ANOMALY,
            severity=AlertSeverity.WARNING,
            title="速度異常",
            is_read=False,
            is_resolved=False,
            created_at=datetime.now(timezone.utc) - timedelta(minutes=2),  # 2分前
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_alert
        self.db.execute.return_value = mock_result

        alert = await self.service.create_alert(
            child_id=self.child.id,
            user_id=self.user.id,
            alert_type=AlertType.SPEED_ANOMALY,
            severity=AlertSeverity.WARNING,
            title="速度異常",
            message="テスト",
        )

        # 既存アラートが返される（新規作成されない）
        assert alert.id == existing_alert.id
        self.db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_from_anomaly(self):
        """異常検知結果からアラート作成"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.db.execute.return_value = mock_result

        anomaly = AnomalyResult(
            is_anomalous=True,
            anomaly_type=AlertType.SPEED_ANOMALY,
            severity=AlertSeverity.CRITICAL,
            confidence=0.9,
            message="車両に乗っている可能性があります",
        )

        alert = await self.service.create_alert_from_anomaly(
            child_id=self.child.id,
            user_id=self.user.id,
            anomaly=anomaly,
            latitude=35.68,
            longitude=139.77,
        )

        assert alert is not None
        self.db.add.assert_called_once()


class TestEscalation:
    """エスカレーションのテスト"""

    @pytest.fixture(autouse=True)
    def setup(self, mock_db):
        self.db = mock_db
        with patch("app.services.alert_service.NotificationService") as mock_notif:
            mock_notif.return_value.send_escalation_notification = AsyncMock(return_value=True)
            self.service = AlertService(self.db)
            self.service.notification_service = mock_notif.return_value

    @pytest.mark.asyncio
    async def test_escalate_info_to_warning(self):
        """info → warning へのエスカレーション"""
        alert = Alert(
            id=uuid.uuid4(),
            child_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            alert_type=AlertType.ROUTE_DEVIATION,
            severity=AlertSeverity.INFO,
            title="ルート逸脱",
            is_read=False,
            is_resolved=False,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = alert
        self.db.execute.return_value = mock_result

        escalated = await self.service.escalate_alert(alert.id)

        assert escalated is not None
        assert escalated.severity == AlertSeverity.WARNING

    @pytest.mark.asyncio
    async def test_escalate_critical_to_emergency(self):
        """critical → emergency へのエスカレーション"""
        alert = Alert(
            id=uuid.uuid4(),
            child_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            alert_type=AlertType.SPEED_ANOMALY,
            severity=AlertSeverity.CRITICAL,
            title="速度異常",
            is_read=False,
            is_resolved=False,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = alert
        self.db.execute.return_value = mock_result

        escalated = await self.service.escalate_alert(alert.id)

        assert escalated.severity == AlertSeverity.EMERGENCY

    @pytest.mark.asyncio
    async def test_no_escalate_emergency(self):
        """emergency はそれ以上エスカレーションしない"""
        alert = Alert(
            id=uuid.uuid4(),
            child_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            alert_type=AlertType.SOS,
            severity=AlertSeverity.EMERGENCY,
            title="SOS",
            is_read=False,
            is_resolved=False,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = alert
        self.db.execute.return_value = mock_result

        escalated = await self.service.escalate_alert(alert.id)

        assert escalated.severity == AlertSeverity.EMERGENCY

    @pytest.mark.asyncio
    async def test_no_escalate_resolved(self):
        """解決済みアラートはエスカレーションしない"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # is_resolved=False条件にマッチしない
        self.db.execute.return_value = mock_result

        escalated = await self.service.escalate_alert(uuid.uuid4())
        assert escalated is None


class TestResolveAlert:
    """アラート解決のテスト"""

    @pytest.fixture(autouse=True)
    def setup(self, mock_db):
        self.db = mock_db
        with patch("app.services.alert_service.NotificationService"):
            self.service = AlertService(self.db)

    @pytest.mark.asyncio
    async def test_resolve_alert(self):
        """アラートを解決済みにする"""
        alert = Alert(
            id=uuid.uuid4(),
            child_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            alert_type=AlertType.SPEED_ANOMALY,
            severity=AlertSeverity.WARNING,
            title="速度異常",
            is_read=False,
            is_resolved=False,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = alert
        self.db.execute.return_value = mock_result

        resolved = await self.service.resolve_alert(alert.id)

        assert resolved.is_resolved is True
        assert resolved.resolved_at is not None

    @pytest.mark.asyncio
    async def test_resolve_nonexistent_alert(self):
        """存在しないアラートの解決はNone"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.db.execute.return_value = mock_result

        result = await self.service.resolve_alert(uuid.uuid4())
        assert result is None


class TestEscalationRules:
    """エスカレーションルールの定義テスト"""

    def test_info_escalation_30min(self):
        assert ESCALATION_RULES[AlertSeverity.INFO]["escalation_after_seconds"] == 1800

    def test_warning_escalation_10min(self):
        assert ESCALATION_RULES[AlertSeverity.WARNING]["escalation_after_seconds"] == 600

    def test_critical_escalation_5min(self):
        assert ESCALATION_RULES[AlertSeverity.CRITICAL]["escalation_after_seconds"] == 300

    def test_emergency_not_in_rules(self):
        assert AlertSeverity.EMERGENCY not in ESCALATION_RULES
