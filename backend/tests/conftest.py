"""テスト共通フィクスチャ"""

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.child import Child, School
from app.models.location import Location
from app.models.route import Route
from app.models.alert import Alert, AlertType, AlertSeverity
from app.models.danger_zone import DangerZone, RiskType, DangerZoneSource


@pytest.fixture
def mock_db():
    """モックDBセッション"""
    db = AsyncMock(spec=AsyncSession)
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def sample_user():
    """テスト用ユーザー"""
    return User(
        id=uuid.uuid4(),
        line_id="test_user_001",
        name="テスト保護者",
        home_latitude=35.6812,
        home_longitude=139.7671,
        onboarding_completed=True,
        is_active=True,
    )


@pytest.fixture
def sample_child(sample_user):
    """テスト用子ども"""
    return Child(
        id=uuid.uuid4(),
        user_id=sample_user.id,
        name="テスト太郎",
        grade=3,
        device_id="BOT_TEST_001",
        is_active=True,
    )


@pytest.fixture
def sample_school():
    """テスト用学校"""
    return School(
        id=uuid.uuid4(),
        name="テスト小学校",
        address="東京都渋谷区テスト1-1",
        latitude=35.6580,
        longitude=139.7016,
        prefecture="東京都",
        city="渋谷区",
    )


@pytest.fixture
def sample_locations(sample_child):
    """テスト用位置情報履歴（通学路上の正常な移動）"""
    base_time = datetime.now(timezone.utc)
    return [
        Location(
            id=uuid.uuid4(),
            child_id=sample_child.id,
            latitude=35.6812 + i * 0.001,
            longitude=139.7671 + i * 0.001,
            speed=1.2,
            accuracy=10.0,
            source="gps_device",
            timestamp=base_time - timedelta(minutes=5 * (4 - i)),
        )
        for i in range(5)
    ]


@pytest.fixture
def sample_danger_zones():
    """テスト用危険ゾーン"""
    return [
        DangerZone(
            id=uuid.uuid4(),
            latitude=35.6850,
            longitude=139.7700,
            radius_meters=100.0,
            risk_level=7,
            risk_type=RiskType.CRIME,
            title="犯罪多発エリア",
            source=DangerZoneSource.POLICE,
            is_active=True,
            verified=True,
        ),
        DangerZone(
            id=uuid.uuid4(),
            latitude=35.6830,
            longitude=139.7680,
            radius_meters=150.0,
            risk_level=4,
            risk_type=RiskType.TRAFFIC,
            title="交通事故多発",
            source=DangerZoneSource.GOVERNMENT,
            is_active=True,
            verified=True,
        ),
    ]


@pytest.fixture
def sample_route(sample_child):
    """テスト用ルート"""
    return Route(
        id=uuid.uuid4(),
        child_id=sample_child.id,
        name="通学路",
        origin_lat=35.6812,
        origin_lng=139.7671,
        destination_lat=35.6580,
        destination_lng=139.7016,
        waypoints_json=[
            {"latitude": 35.6812, "longitude": 139.7671, "order": 0},
            {"latitude": 35.6700, "longitude": 139.7350, "order": 1},
            {"latitude": 35.6580, "longitude": 139.7016, "order": 2},
        ],
        distance_meters=2500.0,
        estimated_duration_minutes=43.0,
        safety_score=7.5,
        is_recommended=True,
        is_active=True,
    )


@pytest.fixture
def sample_alert(sample_child, sample_user):
    """テスト用アラート"""
    return Alert(
        id=uuid.uuid4(),
        child_id=sample_child.id,
        user_id=sample_user.id,
        alert_type=AlertType.SPEED_ANOMALY,
        severity=AlertSeverity.WARNING,
        title="速度異常",
        message="通常より速い移動速度を検知しました",
        latitude=35.6850,
        longitude=139.7700,
        is_read=False,
        is_resolved=False,
    )
