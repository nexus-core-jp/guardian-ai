# Guardian AI - AI防犯プラットフォーム

小学生の安全を守る次世代見守りアプリ。既存のGPS端末と連携し、AIによる安全ルート提案・危険予測・異常検知を提供する。

## コンセプト

```
既存GPS端末:  位置を「追跡」する → 事後に「知る」
Guardian AI: 状況を「理解」する → 事前に「守る」
```

- **ハードウェア不要** — 子どもが既に持っているGPS端末（BoT, みてね, まもサーチ等）と連携
- **設定2分で完了** — 自宅確認→学校選択→GPS端末選択の3ステップ
- **小1でも使える** — 子どもは操作不要。ランドセルにGPS端末を入れるだけ

## 主要機能

| 機能 | 説明 |
|------|------|
| AI安全ルートエンジン | 犯罪統計・不審者情報・時間帯を分析し、毎朝最適な通学路を提案 |
| 地域危険予測マップ | 時間帯×場所のリスクヒートマップをリアルタイム生成 |
| 行動パターン学習 | GPS履歴からAIが通学パターンを学習し、逸脱を即時検知 |
| 速度異常検知 | 徒歩→車速の急変を検知し「車に乗せられた可能性」をアラート |
| 段階的エスカレーション | 情報→注意→警戒→緊急の4段階で自動通知を制御 |
| 見守りコミュニティ | 同じ学区の保護者同士で不審者情報をリアルタイム共有 |

## アーキテクチャ

```
┌──────────────────────┐     ┌──────────────────────────────┐
│  既存GPS端末           │     │  保護者スマホアプリ (Expo)      │
│  BoT/みてね/まもサーチ等 │     │  React Native + TypeScript    │
└──────────┬───────────┘     └──────────────┬───────────────┘
           │ 位置データ                       │ REST API / WebSocket
           ▼                                 ▼
┌───────────────────────────────────────────────────────────┐
│                  Guardian AI バックエンド                    │
│                  FastAPI (Python 3.12)                      │
│                                                             │
│  ┌────────────┐ ┌──────────────┐ ┌───────────────────────┐ │
│  │ 安全ルート    │ │ 危険分析       │ │ 異常検知               │ │
│  │ エンジン      │ │ サービス       │ │ サービス               │ │
│  └────────────┘ └──────────────┘ └───────────────────────┘ │
│  ┌────────────┐ ┌──────────────┐                           │
│  │ アラート      │ │ 通知           │                          │
│  │ エスカレーション│ │ サービス(FCM)  │                           │
│  └────────────┘ └──────────────┘                           │
└───────────────────────┬───────────────────────────────────┘
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
   ┌──────────┐  ┌──────────┐  ┌──────────┐
   │ PostgreSQL│  │  Redis   │  │ 犯罪統計   │
   │ (PostGIS) │  │          │  │ オープンデータ│
   └──────────┘  └──────────┘  └──────────┘
```

## 技術スタック

| レイヤー | 技術 |
|---------|------|
| モバイルアプリ | React Native (Expo) + TypeScript |
| バックエンドAPI | FastAPI (Python 3.12) |
| データベース | PostgreSQL 16 + PostGIS 3.4 |
| キャッシュ | Redis 7 |
| AI/ML | PyTorch (行動分類・異常検知モデル) |
| 地図 | Mapbox GL / Google Maps Platform |
| 通知 | Firebase Cloud Messaging |
| 認証 | LINE Login + JWT |
| コンテナ | Docker Compose |

## セットアップ

### 前提条件

- Docker & Docker Compose
- Python 3.12+
- Node.js 20+
- Expo CLI

### バックエンド

```bash
cd backend

# DB・Redis起動
docker compose up -d db redis

# Python仮想環境
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 環境変数
cp .env.example .env
# .env を編集（LINE_CHANNEL_ID等を設定）

# マイグレーション
alembic upgrade head

# API起動 (port 8002)
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

### モバイルアプリ

```bash
cd mobile
npm install
npx expo start
```

### ポート構成

| ポート | サービス |
|--------|---------|
| 8002 | Guardian AI API |
| 5434 | PostgreSQL |
| 6380 | Redis |

## API エンドポイント

### 認証
- `POST /api/v1/auth/line` — LINE ログイン
- `GET /api/v1/auth/line/callback` — LINE OAuth コールバック
- `POST /api/v1/auth/onboarding` — 初期設定（自宅+学校+子ども登録）
- `GET /api/v1/auth/me` — 現在のユーザー情報

### 子ども管理
- `POST /api/v1/children` — 子ども登録
- `GET /api/v1/children` — 子ども一覧
- `GET/PUT/DELETE /api/v1/children/{id}` — 子ども詳細・更新・削除

### 位置追跡
- `POST /api/v1/locations` — 位置情報記録（GPS端末連携）
- `GET /api/v1/locations/{child_id}/latest` — 最新位置
- `GET /api/v1/locations/{child_id}/history` — 位置履歴

### 安全ルート
- `POST /api/v1/routes/calculate` — AI安全ルート計算
- `GET /api/v1/routes/{child_id}/recommended` — 今日の推奨ルート
- `GET /api/v1/routes/{child_id}` — ルート一覧

### アラート
- `GET /api/v1/alerts` — アラート一覧
- `GET /api/v1/alerts/unread` — 未読数
- `PUT /api/v1/alerts/{id}/read` — 既読にする
- `PUT /api/v1/alerts/{id}/resolve` — 解決済みにする

### 地域コミュニティ
- `GET /api/v1/community/dangers` — 近隣の危険エリア
- `POST /api/v1/community/dangers` — 危険エリア報告
- `GET /api/v1/community/heatmap` — 安全ヒートマップ

## プロジェクト構成

```
guardian-ai/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # APIエンドポイント
│   │   ├── models/          # SQLAlchemyモデル
│   │   ├── schemas/         # Pydanticスキーマ
│   │   ├── services/        # AIサービス・ビジネスロジック
│   │   ├── main.py          # FastAPIアプリ
│   │   ├── config.py        # 設定
│   │   └── database.py      # DB接続
│   ├── alembic/             # マイグレーション
│   ├── docker-compose.yml
│   └── requirements.txt
├── mobile/
│   ├── app/                 # Expo Router画面
│   │   ├── (auth)/          # ログイン
│   │   ├── (onboarding)/    # 初期設定フロー
│   │   └── (main)/          # メインタブ
│   ├── components/          # UIコンポーネント
│   ├── services/            # API・認証・通知
│   ├── stores/              # Zustand状態管理
│   ├── hooks/               # カスタムフック
│   └── types/               # TypeScript型定義
└── data/
    └── schools/             # 小学校マスターデータ
```

## ライセンス

MIT
