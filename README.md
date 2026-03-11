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
| モバイルアプリ | React Native (Expo 55) + TypeScript |
| バックエンドAPI | FastAPI (Python 3.12) |
| データベース | PostgreSQL 16 + PostGIS 3.4 |
| キャッシュ / レートリミット | Redis 7 |
| 地図・ルーティング | OSRM / Mapbox Directions API |
| 通知 | Firebase Cloud Messaging |
| 認証 | LINE Login / Apple Sign-In / Google Sign-In + JWT |
| リアルタイム通信 | WebSocket (位置情報・アラート配信) |
| バックグラウンド処理 | APScheduler (エスカレーション・犯罪データ同期) |
| コンテナ | Docker Compose |
| CI/CD | GitHub Actions + EAS Build |

---

## ローカル開発セットアップ

### 前提条件

- Docker & Docker Compose
- Python 3.12+
- Node.js 22+
- Expo CLI (`npm install -g expo-cli`)

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
# .env を編集（必要に応じてLINE_CHANNEL_ID等を設定）

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

---

## API エンドポイント

### 認証
| メソッド | パス | 説明 |
|---------|------|------|
| POST | `/api/v1/auth/line` | LINE ログイン |
| POST | `/api/v1/auth/apple` | Apple Sign-In ログイン |
| POST | `/api/v1/auth/google` | Google ログイン |
| POST | `/api/v1/auth/refresh` | トークンリフレッシュ (ローテーション方式) |
| POST | `/api/v1/auth/onboarding` | 初期設定（自宅+学校+子ども登録） |
| GET | `/api/v1/auth/me` | 現在のユーザー情報 |
| PUT | `/api/v1/auth/fcm-token` | FCMトークン登録 |

### 子ども管理
| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/v1/children` | 子ども一覧 |
| GET/PUT | `/api/v1/children/{id}` | 子ども詳細・更新 |

### 位置追跡
| メソッド | パス | 説明 |
|---------|------|------|
| POST | `/api/v1/locations` | 位置情報記録（GPS端末連携） |
| GET | `/api/v1/locations/{child_id}/latest` | 最新位置 |
| GET | `/api/v1/locations/{child_id}/history` | 位置履歴 |

### 安全ルート
| メソッド | パス | 説明 |
|---------|------|------|
| POST | `/api/v1/routes/calculate` | AI安全ルート計算 |
| GET | `/api/v1/routes/{child_id}/recommended` | 今日の推奨ルート |
| GET | `/api/v1/routes/{child_id}` | ルート一覧 |

### アラート
| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/v1/alerts` | アラート一覧 (severity/type/readフィルター) |
| GET | `/api/v1/alerts/unread` | 未読数 |
| PUT | `/api/v1/alerts/{id}/read` | 既読にする |
| PUT | `/api/v1/alerts/{id}/resolve` | 解決済みにする |
| PUT | `/api/v1/alerts/read-all` | 全件既読 |

### 地域コミュニティ
| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/v1/community/dangers` | 近隣の危険エリア |
| POST | `/api/v1/community/dangers` | 危険エリア報告 |
| POST | `/api/v1/community/dangers/{id}/confirm` | 危険エリア確認 |
| GET | `/api/v1/community/heatmap` | 安全ヒートマップ |

### 設定・通知
| メソッド | パス | 説明 |
|---------|------|------|
| PATCH | `/api/v1/settings/profile` | プロフィール更新 |
| PATCH | `/api/v1/settings/home-location` | 自宅位置更新 |
| DELETE | `/api/v1/settings/account` | アカウント削除 (匿名化) |
| GET | `/api/v1/notifications/preferences` | 通知設定取得 |
| PATCH | `/api/v1/notifications/preferences` | 通知設定更新 |

### GPSデバイス・WebSocket
| メソッド | パス | 説明 |
|---------|------|------|
| POST | `/api/v1/devices/webhook/{device_type}` | GPSデバイスWebhook |
| WS | `/api/v1/ws?token={jwt}` | リアルタイム位置・アラート配信 |

---

## プロジェクト構成

```
guardian-ai/
├── .github/workflows/       # CI/CD (GitHub Actions)
│   ├── backend-ci.yml       # Lint → Test → Docker Build → Deploy
│   └── mobile-ci.yml        # TypeCheck → Test → EAS Build
├── backend/
│   ├── app/
│   │   ├── api/v1/          # APIエンドポイント
│   │   ├── models/          # SQLAlchemyモデル
│   │   ├── schemas/         # Pydanticスキーマ
│   │   ├── services/        # ビジネスロジック
│   │   ├── middleware/       # セキュリティ・レートリミット
│   │   ├── main.py          # FastAPIアプリ
│   │   ├── config.py        # 設定
│   │   └── database.py      # DB接続
│   ├── tests/               # pytest テスト
│   ├── alembic/             # マイグレーション
│   ├── docker-compose.yml           # 開発環境
│   ├── docker-compose.production.yml # 本番環境
│   ├── Dockerfile
│   └── requirements.txt
├── mobile/
│   ├── app/                 # Expo Router画面
│   │   ├── (auth)/          # ログイン
│   │   ├── (onboarding)/    # 初期設定フロー
│   │   └── (main)/          # メインタブ (地図/通知/コミュニティ/設定)
│   ├── components/          # UIコンポーネント
│   ├── services/            # API・認証・通知・位置情報
│   ├── stores/              # Zustand状態管理
│   ├── hooks/               # カスタムフック
│   ├── __tests__/           # Jest テスト
│   ├── types/               # TypeScript型定義
│   ├── eas.json             # EAS Build設定
│   └── package.json
└── data/
    └── schools/             # 小学校マスターデータ
```

---

## 本番デプロイガイド

### 1. 外部サービスの設定

以下のサービスでアカウント・プロジェクトを作成し、必要な認証情報を取得する。

#### LINE Login

| 設定項目 | 取得先 |
|----------|--------|
| `LINE_CHANNEL_ID` | [LINE Developers Console](https://developers.line.biz/) → チャネル基本設定 |
| `LINE_CHANNEL_SECRET` | 同上 |
| `LINE_REDIRECT_URI` | チャネル設定の「コールバックURL」に `https://api.guardian-ai.jp/api/v1/auth/line/callback` を登録 |

**手順:**
1. LINE Developers Console でプロバイダー作成
2. 「LINE ログイン」チャネルを作成
3. チャネル基本設定から Channel ID / Channel Secret をコピー
4. 「LINE ログイン設定」のコールバックURLに本番URLを追加
5. OpenID Connect のメール取得を有効化

#### Apple Sign-In

| 設定項目 | 取得先 |
|----------|--------|
| `APPLE_TEAM_ID` | [Apple Developer](https://developer.apple.com/) → Membership |
| `APPLE_BUNDLE_ID` | `com.guardianai.app` (app.jsonと一致させる) |

**手順:**
1. Apple Developer Program に登録 (年間 $99)
2. Certificates, Identifiers & Profiles → Identifiers で App ID 登録
3. 「Sign In with Apple」Capability を有効化
4. Team ID をメモ（Membership ページに記載）

#### Google Sign-In

| 設定項目 | 取得先 |
|----------|--------|
| `GOOGLE_CLIENT_ID` | [Google Cloud Console](https://console.cloud.google.com/) |

**手順:**
1. Google Cloud Console でプロジェクト作成
2. 「APIとサービス」→「認証情報」→「OAuth 2.0 クライアント ID」を作成
   - iOS: バンドルID `com.guardianai.app` を登録
   - Android: パッケージ名 `com.guardianai.app` + SHA-1 フィンガープリントを登録
   - Web: 承認済みリダイレクトURIを設定
3. Client ID をコピー

#### Firebase Cloud Messaging (プッシュ通知)

| 設定項目 | 取得先 |
|----------|--------|
| `FCM_CREDENTIALS_PATH` | Firebase Console → プロジェクト設定 → サービスアカウント |

**手順:**
1. [Firebase Console](https://console.firebase.google.com/) でプロジェクト作成
2. 「プロジェクト設定」→「サービスアカウント」→「新しい秘密鍵を生成」
3. ダウンロードしたJSONを `backend/credentials/firebase.json` に配置
4. iOS: APNs認証キー(.p8)をFirebaseにアップロード
5. Android: `google-services.json` をExpoプロジェクトに追加

#### 地図API (OSRM / Mapbox)

| 設定項目 | 取得先 |
|----------|--------|
| `MAPBOX_TOKEN` | [Mapbox](https://www.mapbox.com/) → Account → Access Tokens |
| `GOOGLE_MAPS_API_KEY` | Google Cloud Console → APIとサービス → 認証情報 |

**注意:** OSRM をセルフホスト (無料) する場合は、Mapbox Token は不要。`backend/app/services/route_engine.py` の `OSRM_URL` を自前サーバーに変更する。

---

### 2. サーバー構築

#### 推奨スペック

| 項目 | 最小 | 推奨 |
|------|------|------|
| CPU | 2 vCPU | 4 vCPU |
| メモリ | 4 GB | 8 GB |
| ストレージ | 40 GB SSD | 80 GB SSD |
| OS | Ubuntu 22.04+ | Ubuntu 24.04 LTS |

#### サーバー設定

```bash
# Docker インストール
curl -fsSL https://get.docker.com | sh

# プロジェクト配置
mkdir -p /opt/guardian-ai/credentials
cd /opt/guardian-ai

# 本番環境変数を設定
cp .env.production.example .env
# .env を編集して全ての必須項目を設定

# SECRET_KEY を安全に生成
echo "SECRET_KEY=$(openssl rand -hex 32)" >> .env

# Firebase credentials 配置
cp /path/to/firebase.json credentials/firebase.json

# 起動
docker compose -f docker-compose.production.yml up -d

# マイグレーション実行
docker compose -f docker-compose.production.yml exec api alembic upgrade head

# ログ確認
docker compose -f docker-compose.production.yml logs -f api
```

#### SSL/ドメイン設定 (Caddy推奨)

```bash
# Caddyfile (/etc/caddy/Caddyfile)
api.guardian-ai.jp {
    reverse_proxy localhost:8002
}
```

Caddy は Let's Encrypt 証明書を自動取得・更新する。

---

### 3. モバイルアプリビルド

#### Expo アカウント設定

```bash
# Expoにログイン
npx eas login

# プロジェクトを初期化 (初回のみ)
cd mobile
npx eas init
```

#### ビルド実行

```bash
# プレビュー版 (内部テスト用)
npx eas build --profile preview --platform all

# 本番版 (ストア提出用)
npx eas build --profile production --platform all
```

#### ストア提出

```bash
# App Store Connect に提出
npx eas submit --platform ios

# Google Play Console に提出
npx eas submit --platform android
```

---

### 4. App Store / Google Play 申請準備

#### 共通で必要なもの

| 項目 | 内容 |
|------|------|
| アプリ名 | Guardian AI |
| カテゴリ | ライフスタイル / ペアレンタルコントロール |
| 対象年齢 | 4+ (iOS) / 全ユーザー (Android) |
| プライバシーポリシーURL | `https://guardian-ai.jp/privacy` |
| 利用規約URL | `https://guardian-ai.jp/terms` |
| サポートURL | `https://guardian-ai.jp/support` |
| スクリーンショット | iPhone 6.7" / 6.1" + Android Phone |
| 説明文 | 日本語 (1,000文字以内の概要 + 4,000文字以内の詳細) |

#### Apple App Store 固有

| 項目 | 内容 |
|------|------|
| Apple Developer Program | 年間 $99 (個人) / $299 (法人) |
| App Store Connect | アプリレコード作成、価格設定 (無料) |
| App Privacy | 位置情報・通知データの使用目的を申告 |
| 位置情報の使用目的文 | 「お子様の安全を見守るために位置情報を使用します」 |
| バックグラウンド位置情報 | Background Modes → Location Updates を有効化し、審査用に利用理由を詳細説明 |

**審査のポイント:**
- 位置情報の使用理由をスクリーンショットと合わせて詳しく説明する
- 子どもの情報を扱うため、COPPA/児童プライバシーに関する準拠を明記
- アプリ内でのアカウント削除機能が実装済み (必須要件)

#### Google Play Store 固有

| 項目 | 内容 |
|------|------|
| Google Play Console | 登録料 $25 (一回限り) |
| データセーフティセクション | 位置情報・個人情報の収集/共有/保持を申告 |
| ターゲットオーディエンス | 保護者向け (子ども向けではない) |
| テストトラック | Internal Test → Closed Test → Open Test → Production |

---

### 5. GitHub Actions CI/CD 設定

#### 必要な GitHub Secrets

リポジトリの Settings → Secrets and variables → Actions で以下を設定:

| Secret名 | 説明 | 必須 |
|-----------|------|------|
| `EXPO_TOKEN` | Expo アカウントトークン (`npx eas login` で生成) | モバイルビルド |
| `STAGING_HOST` | ステージングサーバーのホスト名/IP | バックエンドデプロイ |
| `STAGING_SSH_KEY` | デプロイ用SSH秘密鍵 | バックエンドデプロイ |

#### GitHub Environments 設定

Settings → Environments で `staging` 環境を作成し、必要に応じて承認者を設定。

---

### 6. リリース前チェックリスト

```
本番環境変数:
  [ ] SECRET_KEY を openssl rand -hex 32 で生成済み
  [ ] DEBUG=false を確認
  [ ] LINE_CHANNEL_ID / LINE_CHANNEL_SECRET を設定済み
  [ ] LINE_REDIRECT_URI を本番URLに変更済み
  [ ] APPLE_TEAM_ID を設定済み
  [ ] GOOGLE_CLIENT_ID を設定済み
  [ ] FCM credentials JSON を配置済み
  [ ] CORS_ORIGINS を本番ドメインに設定済み
  [ ] POSTGRES_PASSWORD を強いパスワードに設定済み
  [ ] REDIS_PASSWORD を設定済み

サーバー:
  [ ] Docker + Docker Compose インストール済み
  [ ] SSL証明書取得済み (Caddy / Let's Encrypt)
  [ ] ファイアウォール設定済み (80, 443のみ公開)
  [ ] docker compose -f docker-compose.production.yml up -d で起動確認
  [ ] alembic upgrade head でマイグレーション完了
  [ ] /health エンドポイントで200応答確認

モバイル:
  [ ] eas.json の production 環境変数を本番APIに設定済み
  [ ] app.json の version を正しく設定
  [ ] eas build --profile production で本番ビルド成功
  [ ] 実機テストでログイン→オンボーディング→地図表示が動作確認

ストア申請:
  [ ] プライバシーポリシーページを公開済み
  [ ] 利用規約ページを公開済み
  [ ] スクリーンショットを撮影済み
  [ ] 説明文を作成済み
  [ ] App Store / Google Play でアプリレコード作成済み
  [ ] eas submit で提出完了
```

---

## テスト

### バックエンド

```bash
cd backend
pytest tests/ -v
```

### モバイル

```bash
cd mobile
npm test
npm run test:coverage
```

---

## ライセンス

MIT
