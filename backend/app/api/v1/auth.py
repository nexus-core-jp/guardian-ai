"""認証エンドポイント（LINE ログイン）"""

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.models.child import Child
from app.schemas.user import (
    LINELoginRequest,
    TokenResponse,
    UserResponse,
    OnboardingRequest,
    OnboardingResponse,
)
from app.api.deps import create_access_token, get_current_user
from app.services.route_engine import RouteEngine

router = APIRouter()
settings = get_settings()

LINE_TOKEN_URL = "https://api.line.me/oauth2/v2.1/token"
LINE_PROFILE_URL = "https://api.line.me/v2/profile"


@router.post("/line", response_model=TokenResponse, summary="LINEログイン")
async def line_login(
    request: LINELoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    LINE認証コードを使ってログイン/新規登録を行う。
    LINEからアクセストークンを取得し、プロフィール情報を取得してユーザーを作成/取得する。
    """
    # LINE認証コードでアクセストークンを取得
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            LINE_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": request.code,
                "redirect_uri": settings.LINE_REDIRECT_URI,
                "client_id": settings.LINE_CHANNEL_ID,
                "client_secret": settings.LINE_CHANNEL_SECRET,
            },
        )

        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="LINE認証に失敗しました",
            )

        token_data = token_response.json()
        line_access_token = token_data.get("access_token")

        # LINEプロフィール取得
        profile_response = await client.get(
            LINE_PROFILE_URL,
            headers={"Authorization": f"Bearer {line_access_token}"},
        )

        if profile_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="LINEプロフィールの取得に失敗しました",
            )

        profile = profile_response.json()

    line_id = profile["userId"]
    display_name = profile.get("displayName", "ユーザー")
    picture_url = profile.get("pictureUrl")

    # 既存ユーザーを検索
    result = await db.execute(select(User).where(User.line_id == line_id))
    user = result.scalar_one_or_none()

    if user is None:
        # 新規ユーザー作成
        user = User(
            line_id=line_id,
            name=display_name,
            avatar_url=picture_url,
        )
        db.add(user)
        await db.flush()

    # JWTトークン生成
    access_token = create_access_token(user.id)

    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.get("/line/callback", response_model=TokenResponse, summary="LINE OAuth コールバック")
async def line_callback(
    code: str,
    state: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    LINE OAuthリダイレクト先のコールバックエンドポイント。
    認証コードを受け取り、ログイン処理を行う。
    """
    request = LINELoginRequest(code=code, state=state)
    return await line_login(request=request, db=db)


@router.post("/onboarding", response_model=OnboardingResponse, summary="初期セットアップ")
async def onboarding(
    request: OnboardingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    初期セットアップ: 自宅位置、学校、子ども情報を登録し、初回推奨ルートを計算する。
    """
    # 自宅位置を更新
    current_user.home_latitude = request.home_latitude
    current_user.home_longitude = request.home_longitude
    current_user.onboarding_completed = True

    # 子どもプロフィール作成
    child = Child(
        user_id=current_user.id,
        name=request.child_name,
        grade=request.child_grade,
        school_id=request.school_id,
    )
    db.add(child)
    await db.flush()

    # 推奨ルート計算を試みる（学校情報がある場合）
    recommended_route_id = None
    if request.school_id:
        try:
            route_engine = RouteEngine(db)
            route = await route_engine.calculate_safe_route(
                origin_lat=request.home_latitude,
                origin_lng=request.home_longitude,
                destination_lat=None,
                destination_lng=None,
                child_id=child.id,
                school_id=request.school_id,
            )
            if route:
                recommended_route_id = route.route.id
        except Exception:
            pass

    return OnboardingResponse(
        user=UserResponse.model_validate(current_user),
        child_id=child.id,
        recommended_route_id=recommended_route_id,
        message="セットアップが完了しました。お子様の安全を見守ります。",
    )


@router.post("/dev-login", response_model=TokenResponse, summary="開発用ログイン")
async def dev_login(db: AsyncSession = Depends(get_db)):
    """
    開発環境専用: テストユーザーを作成/取得してログインする。
    本番環境では無効化すること。
    """
    if not settings.DEBUG:
        raise HTTPException(status_code=404, detail="Not Found")

    line_id = "dev_test_user"
    result = await db.execute(select(User).where(User.line_id == line_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            line_id=line_id,
            name="テスト保護者",
        )
        db.add(user)
        await db.flush()

    access_token = create_access_token(user.id)
    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse, summary="現在のユーザー情報")
async def get_me(current_user: User = Depends(get_current_user)):
    """現在ログイン中のユーザー情報を返す"""
    return UserResponse.model_validate(current_user)
