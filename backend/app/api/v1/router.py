"""v1 APIルーター"""

from fastapi import APIRouter

from app.api.v1 import auth, children, locations, routes, alerts, community, schools

v1_router = APIRouter(tags=["v1"])

v1_router.include_router(auth.router, prefix="/auth", tags=["認証"])
v1_router.include_router(children.router, prefix="/children", tags=["子ども管理"])
v1_router.include_router(locations.router, prefix="/locations", tags=["位置情報"])
v1_router.include_router(routes.router, prefix="/routes", tags=["安全ルート"])
v1_router.include_router(alerts.router, prefix="/alerts", tags=["アラート"])
v1_router.include_router(community.router, prefix="/community", tags=["コミュニティ"])
v1_router.include_router(schools.router, prefix="/schools", tags=["学校検索"])
