# HUNTER-v2

AI エージェントチームによる Twitter アカウント成長システム。

## 概要

5つの AI エージェントが協調して、テック/AI ジャンルの Twitter アカウントを0からフォロワー獲得まで自動支援します。

**ハイブリッド API 構成:**
- **投稿** → Twitter 公式 API（Free tier, $0）
- **読み取り・分析** → サードパーティ API（SociaVault / TwitterAPI.io）

## エージェントチーム

| エージェント | 役割 |
|---|---|
| **Orchestrator** | 全体調整・ワークフロー管理 |
| **Content Strategist** | トレンド分析・週間コンテンツ計画 |
| **Content Creator** | ツイート文面の生成 |
| **Engagement Analyst** | パフォーマンス分析・改善提案 |
| **Community Manager** | リプライ案・エンゲージメント戦略 |

## セットアップ

```bash
# 依存関係インストール
pip install -e .

# 環境変数設定
cp .env.example .env
# .env を編集して API キーを設定
```

## 使い方

```bash
# システム状況確認
hunter status

# 週間コンテンツ計画を生成
hunter plan

# ツイート原稿を生成
hunter create

# 原稿を確認・承認
hunter review

# 承認済みツイートを投稿
hunter post

# トレンド検索
hunter search -q "AI LLM"

# 競合アカウントのツイート閲覧
hunter spy username

# エンゲージメント提案を取得
hunter engage

# アナリティクス手動追加
hunter analytics add --tweet-id 1 --likes 10 --retweets 5

# アナリティクスレポート
hunter analytics report
```

## 技術スタック

- Python 3.11+
- Claude API (anthropic SDK)
- tweepy (Twitter API v2)
- SociaVault / TwitterAPI.io
- SQLite / Click / PyYAML
