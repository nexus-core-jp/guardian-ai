"""子ども管理エンドポイント"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.child import Child
from app.schemas.child import (
    ChildCreate,
    ChildUpdate,
    ChildResponse,
    ChildListResponse,
)
from app.api.deps import get_current_user

router = APIRouter()


@router.get("", response_model=ChildListResponse, summary="子ども一覧取得")
async def list_children(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """現在のユーザーに紐づく子ども一覧を取得する"""
    result = await db.execute(
        select(Child)
        .where(Child.user_id == current_user.id, Child.is_active == True)
        .order_by(Child.created_at)
    )
    children = result.scalars().all()

    count_result = await db.execute(
        select(func.count())
        .select_from(Child)
        .where(Child.user_id == current_user.id, Child.is_active == True)
    )
    total = count_result.scalar() or 0

    return ChildListResponse(
        children=[ChildResponse.model_validate(c) for c in children],
        total=total,
    )


@router.post(
    "", response_model=ChildResponse, status_code=status.HTTP_201_CREATED,
    summary="子ども登録",
)
async def create_child(
    data: ChildCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """新しい子どもプロフィールを登録する"""
    child = Child(
        user_id=current_user.id,
        name=data.name,
        grade=data.grade,
        school_id=data.school_id,
        device_id=data.device_id,
    )
    db.add(child)
    await db.flush()
    await db.refresh(child)

    return ChildResponse.model_validate(child)


@router.get("/{child_id}", response_model=ChildResponse, summary="子ども詳細取得")
async def get_child(
    child_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """子どもの詳細情報を取得する"""
    result = await db.execute(
        select(Child).where(
            Child.id == child_id,
            Child.user_id == current_user.id,
        )
    )
    child = result.scalar_one_or_none()

    if child is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="子どもの情報が見つかりません",
        )

    return ChildResponse.model_validate(child)


@router.put("/{child_id}", response_model=ChildResponse, summary="子ども情報更新")
async def update_child(
    child_id: uuid.UUID,
    data: ChildUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """子どもプロフィールを更新する"""
    result = await db.execute(
        select(Child).where(
            Child.id == child_id,
            Child.user_id == current_user.id,
        )
    )
    child = result.scalar_one_or_none()

    if child is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="子どもの情報が見つかりません",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(child, field, value)

    await db.flush()
    await db.refresh(child)

    return ChildResponse.model_validate(child)


@router.delete("/{child_id}", status_code=status.HTTP_204_NO_CONTENT, summary="子ども削除")
async def delete_child(
    child_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """子どもプロフィールを論理削除する"""
    result = await db.execute(
        select(Child).where(
            Child.id == child_id,
            Child.user_id == current_user.id,
        )
    )
    child = result.scalar_one_or_none()

    if child is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="子どもの情報が見つかりません",
        )

    child.is_active = False
    await db.flush()
