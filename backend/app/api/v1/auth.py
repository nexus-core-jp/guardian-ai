"""認証エンドポイント（LINE / Apple / Google ログイン）"""

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt as jose_jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.models.child import Child
from app.schemas.user import (
    LINELoginRequest,
    AppleLoginRequest,
    GoogleLoginRequest,
    TokenResponse,
    UserResponse,
    OnboardingRequest,
    OnboardingResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
)
from app.api.deps import create_access_token, create_refresh_token, verify_refresh_token, get_current_user
from app.services.route_engine import RouteEngine

logger = logging.getLogger(__name__)

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
    refresh_token = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
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


@router.post("/apple", response_model=TokenResponse, summary="Apple Sign-Inログイン")
async def apple_login(
    request: AppleLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Apple ID Tokenを検証してログイン/新規登録を行う。
    """
    try:
        # Apple公開鍵を取得してJWTを検証
        async with httpx.AsyncClient() as client:
            jwks_response = await client.get("https://appleid.apple.com/auth/keys")
            jwks = jwks_response.json()

        # ヘッダーからkidを取得
        unverified_header = jose_jwt.get_unverified_header(request.id_token)
        kid = unverified_header.get("kid")

        # 一致する公開鍵を探す
        key = None
        for k in jwks.get("keys", []):
            if k["kid"] == kid:
                key = k
                break

        if key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Apple公開鍵の検証に失敗しました",
            )

        # JWTを検証（python-joseはJWKから直接検証可能）
        payload = jose_jwt.decode(
            request.id_token,
            key,
            algorithms=["RS256"],
            audience=settings.APPLE_BUNDLE_ID,
            issuer="https://appleid.apple.com",
        )

    except JWTError as e:
        logger.warning(f"Apple ID Token検証失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Apple認証に失敗しました",
        )

    apple_sub = payload.get("sub")
    apple_email = payload.get("email")

    if not apple_sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Apple IDの取得に失敗しました",
        )

    # 既存ユーザーを検索
    result = await db.execute(select(User).where(User.apple_id == apple_sub))
    user = result.scalar_one_or_none()

    # Apple IDで見つからない場合、メールで既存アカウントを検索してリンク
    if user is None and apple_email:
        result = await db.execute(select(User).where(User.email == apple_email))
        user = result.scalar_one_or_none()
        if user:
            user.apple_id = apple_sub

    if user is None:
        display_name = request.full_name or "ユーザー"
        user = User(
            apple_id=apple_sub,
            email=apple_email,
            name=display_name,
        )
        db.add(user)
        await db.flush()

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/google", response_model=TokenResponse, summary="Googleログイン")
async def google_login(
    request: GoogleLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Google ID Tokenを検証してログイン/新規登録を行う。
    GoogleのtokeninfoエンドポイントでIDトークンを検証する。
    """
    # Google ID Tokenを検証
    async with httpx.AsyncClient() as client:
        verify_response = await client.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": request.id_token},
        )

        if verify_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google認証に失敗しました",
            )

        payload = verify_response.json()

    # aud（クライアントID）の検証
    if settings.GOOGLE_CLIENT_ID and payload.get("aud") != settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google認証の検証に失敗しました",
        )

    google_sub = payload.get("sub")
    google_email = payload.get("email")
    google_name = payload.get("name", "ユーザー")
    google_picture = payload.get("picture")

    if not google_sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google IDの取得に失敗しました",
        )

    # 既存ユーザーを検索
    result = await db.execute(select(User).where(User.google_id == google_sub))
    user = result.scalar_one_or_none()

    # Google IDで見つからない場合、メールで既存アカウントを検索してリンク
    if user is None and google_email:
        result = await db.execute(select(User).where(User.email == google_email))
        user = result.scalar_one_or_none()
        if user:
            user.google_id = google_sub

    if user is None:
        user = User(
            google_id=google_sub,
            email=google_email,
            name=google_name,
            avatar_url=google_picture,
        )
        db.add(user)
        await db.flush()

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
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
    refresh_token = create_refresh_token(user.id)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/logout", status_code=status.HTTP_200_OK, summary="ログアウト")
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    ログアウト処理。FCMトークンをクリアしてプッシュ通知を停止する。
    JWT自体はステートレスのためサーバー側での無効化は行わない。
    """
    if current_user.fcm_token:
        current_user.fcm_token = None
        await db.flush()
    return {"status": "ok", "message": "ログアウトしました"}


@router.get("/me", response_model=UserResponse, summary="現在のユーザー情報")
async def get_me(current_user: User = Depends(get_current_user)):
    """現在ログイン中のユーザー情報を返す"""
    return UserResponse.model_validate(current_user)


@router.post("/refresh", response_model=RefreshTokenResponse, summary="トークンリフレッシュ")
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    リフレッシュトークンを使って新しいアクセストークンとリフレッシュトークンを取得する。
    リフレッシュトークンはローテーション方式（使用済みトークンは無効化される）。
    """
    user_id = verify_refresh_token(request.refresh_token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なリフレッシュトークンです",
        )

    # ユーザーの存在確認
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザーが見つかりません",
        )

    # 新しいトークンペアを発行（ローテーション）
    new_access_token = create_access_token(user.id)
    new_refresh_token = create_refresh_token(user.id)

    return RefreshTokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
    )


@router.put("/fcm-token", status_code=status.HTTP_200_OK, summary="FCMトークン更新")
async def update_fcm_token(
    fcm_token: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """プッシュ通知用のFCMトークンを更新する"""
    current_user.fcm_token = fcm_token
    await db.flush()
    return {"status": "ok"}
