"""危険エリア分析サービス"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.danger_zone import DangerZone, RiskType


class TimeOfDay(str, Enum):
    MORNING = "morning"      # 6-9時
    DAYTIME = "daytime"      # 9-15時
    AFTERNOON = "afternoon"  # 15-18時
    EVENING = "evening"      # 18-21時
    NIGHT = "night"          # 21-6時


@dataclass
class RiskScoreBreakdown:
    """リスクスコアの内訳"""
    overall: float
    crime_risk: float
    traffic_risk: float
    lighting_risk: float
    suspicious_person_risk: float
    natural_hazard_risk: float


@dataclass
class AreaRiskResult:
    """エリアリスク分析結果"""
    latitude: float
    longitude: float
    radius_meters: float
    risk_score: RiskScoreBreakdown
    danger_zones_count: int
    highest_risk_type: str | None
    recommendation: str


class DangerAnalyzer:
    """
    危険エリア分析サービス
    犯罪統計、不審者報告、照明データ、交通データを組み合わせて
    エリアのリスクレベルを算出する。
    """

    # リスク種別ごとの重み
    RISK_WEIGHTS = {
        RiskType.SUSPICIOUS_PERSON: 1.5,
        RiskType.CRIME: 2.0,
        RiskType.TRAFFIC: 1.2,
        RiskType.DARK_AREA: 1.0,
        RiskType.CONSTRUCTION: 0.8,
        RiskType.NATURAL_HAZARD: 1.8,
        RiskType.OTHER: 0.5,
    }

    # 時間帯による補正係数
    TIME_MULTIPLIERS = {
        TimeOfDay.MORNING: 0.7,
        TimeOfDay.DAYTIME: 0.5,
        TimeOfDay.AFTERNOON: 0.8,
        TimeOfDay.EVENING: 1.3,
        TimeOfDay.NIGHT: 1.8,
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze_area_risk(
        self,
        latitude: float,
        longitude: float,
        radius_meters: float = 500.0,
        time: datetime | None = None,
    ) -> AreaRiskResult:
        """
        指定エリアのリスクを分析する。

        Args:
            latitude: 中心緯度
            longitude: 中心経度
            radius_meters: 分析半径（メートル）
            time: 分析対象時刻

        Returns:
            エリアリスク分析結果
        """
        if time is None:
            time = datetime.now(timezone.utc)

        time_of_day = self._get_time_of_day(time)
        time_multiplier = self.TIME_MULTIPLIERS.get(time_of_day, 1.0)

        # 近隣の危険エリアを取得
        danger_zones = await self._get_danger_zones_in_area(
            latitude, longitude, radius_meters
        )

        # カテゴリ別リスクスコアを計算
        crime_risk = 0.0
        traffic_risk = 0.0
        lighting_risk = 0.0
        suspicious_risk = 0.0
        natural_risk = 0.0
        highest_risk_level = 0
        highest_risk_type = None

        for zone in danger_zones:
            weight = self.RISK_WEIGHTS.get(
                RiskType(zone.risk_type) if isinstance(zone.risk_type, str) else zone.risk_type,
                1.0
            )
            weighted_score = zone.risk_level * weight * time_multiplier

            if zone.risk_level > highest_risk_level:
                highest_risk_level = zone.risk_level
                highest_risk_type = zone.risk_type

            risk_type = zone.risk_type
            if isinstance(risk_type, str):
                try:
                    risk_type = RiskType(risk_type)
                except ValueError:
                    risk_type = RiskType.OTHER

            if risk_type == RiskType.CRIME:
                crime_risk += weighted_score
            elif risk_type == RiskType.TRAFFIC:
                traffic_risk += weighted_score
            elif risk_type == RiskType.DARK_AREA:
                lighting_risk += weighted_score
            elif risk_type == RiskType.SUSPICIOUS_PERSON:
                suspicious_risk += weighted_score
            elif risk_type == RiskType.NATURAL_HAZARD:
                natural_risk += weighted_score

        # スコアを1-10に正規化
        def normalize(score: float) -> float:
            return min(10.0, max(1.0, score))

        crime_risk = normalize(crime_risk)
        traffic_risk = normalize(traffic_risk)
        lighting_risk = normalize(lighting_risk)
        suspicious_risk = normalize(suspicious_risk)
        natural_risk = normalize(natural_risk)

        # 総合スコア（加重平均）
        overall = (
            crime_risk * 0.3
            + traffic_risk * 0.2
            + lighting_risk * 0.15
            + suspicious_risk * 0.25
            + natural_risk * 0.1
        )
        overall = normalize(overall)

        # 推奨メッセージ生成
        recommendation = self._generate_recommendation(
            overall, highest_risk_type, time_of_day
        )

        return AreaRiskResult(
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_meters,
            risk_score=RiskScoreBreakdown(
                overall=round(overall, 1),
                crime_risk=round(crime_risk, 1),
                traffic_risk=round(traffic_risk, 1),
                lighting_risk=round(lighting_risk, 1),
                suspicious_person_risk=round(suspicious_risk, 1),
                natural_hazard_risk=round(natural_risk, 1),
            ),
            danger_zones_count=len(danger_zones),
            highest_risk_type=highest_risk_type,
            recommendation=recommendation,
        )

    async def _get_danger_zones_in_area(
        self,
        latitude: float,
        longitude: float,
        radius_meters: float,
    ) -> list[DangerZone]:
        """指定エリア内の危険ゾーンを取得する"""
        # 緯度1度 ≈ 111km, 経度1度 ≈ 91km（日本の平均）
        lat_range = radius_meters / 111000.0
        lng_range = radius_meters / 91000.0

        result = await self.db.execute(
            select(DangerZone).where(
                DangerZone.is_active == True,
                DangerZone.latitude >= latitude - lat_range,
                DangerZone.latitude <= latitude + lat_range,
                DangerZone.longitude >= longitude - lng_range,
                DangerZone.longitude <= longitude + lng_range,
                (DangerZone.expires_at == None) |
                (DangerZone.expires_at > datetime.now(timezone.utc)),
            )
        )
        return list(result.scalars().all())

    @staticmethod
    def _get_time_of_day(time: datetime) -> TimeOfDay:
        """時刻から時間帯を判定する"""
        hour = time.hour
        if 6 <= hour < 9:
            return TimeOfDay.MORNING
        elif 9 <= hour < 15:
            return TimeOfDay.DAYTIME
        elif 15 <= hour < 18:
            return TimeOfDay.AFTERNOON
        elif 18 <= hour < 21:
            return TimeOfDay.EVENING
        else:
            return TimeOfDay.NIGHT

    @staticmethod
    def _generate_recommendation(
        overall_risk: float,
        highest_risk_type: str | None,
        time_of_day: TimeOfDay,
    ) -> str:
        """リスクに基づいた推奨メッセージを生成する"""
        messages = []

        if overall_risk >= 7:
            messages.append("⚠️ このエリアは現在リスクが高い状態です。できるだけ別のルートを使用してください。")
        elif overall_risk >= 5:
            messages.append("このエリアには注意が必要です。お子様の見守りを強化してください。")
        else:
            messages.append("このエリアは比較的安全です。")

        if highest_risk_type:
            risk_messages = {
                "suspicious_person": "不審者の報告があります。",
                "crime": "犯罪リスクが報告されています。",
                "traffic": "交通事故のリスクがあります。横断歩道を使用してください。",
                "dark_area": "照明が不足しているエリアがあります。",
                "construction": "工事中のエリアがあります。迂回してください。",
                "natural_hazard": "自然災害のリスクがあります。",
            }
            msg = risk_messages.get(highest_risk_type)
            if msg:
                messages.append(msg)

        if time_of_day in (TimeOfDay.EVENING, TimeOfDay.NIGHT):
            messages.append("夜間は特に注意が必要です。明るい道を選んでください。")

        return " ".join(messages)
