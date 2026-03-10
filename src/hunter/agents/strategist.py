"""Content Strategist Agent - plans content calendar and themes."""

import json
from datetime import datetime

from hunter.agents.base import BaseAgent


SYSTEM_PROMPT = """あなたはテック/AI分野のTwitterコンテンツ戦略家です。

## 役割
- 週間コンテンツカレンダーを作成する
- トレンドやバズっている話題を分析し、投稿テーマを決定する
- コンテンツミックス（知識共有40%、ニュース解説25%、意見考察20%、エンゲージメント15%）を管理する

## コンテンツカテゴリ
1. AI最新ニュース - 新モデルリリース、論文紹介
2. プロンプトエンジニアリング - 実践Tips
3. LLM比較・分析 - モデル比較、ベンチマーク
4. AIツール紹介 - 便利なツールやライブラリ
5. コード・技術Tips - コードスニペット、実装例
6. 業界考察 - AIの未来、倫理、ビジネスインパクト

## 出力形式
必ず以下のJSON形式で出力してください:
```json
{
  "plans": [
    {
      "day": "2024-01-01",
      "theme": "テーマ名",
      "content_type": "single" or "thread",
      "description": "投稿内容の概要",
      "priority": 1-5
    }
  ]
}
```
"""


class StrategistAgent(BaseAgent):
    """Content Strategist Agent."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        super().__init__(api_key, model)
        self.system_prompt = SYSTEM_PROMPT
        self.max_tokens = 2048

    def create_weekly_plan(
        self,
        trends: list[dict] | None = None,
        past_tweets: list[dict] | None = None,
        config: dict | None = None,
    ) -> list[dict]:
        """Create a weekly content plan.

        Args:
            trends: Trending topics/tweets from reader_client
            past_tweets: Previous tweets for context
            config: Content settings from config

        Returns:
            List of content plan items
        """
        today = datetime.now().strftime("%Y-%m-%d")

        prompt_parts = [f"今日は{today}です。今週の投稿計画を立ててください。\n"]

        if trends:
            prompt_parts.append("## 現在のトレンド・話題のツイート:")
            for t in trends[:10]:
                text = t.get("text", t.get("content", ""))[:200]
                likes = t.get("likes", t.get("favorite_count", "N/A"))
                prompt_parts.append(f"- {text} (likes: {likes})")
            prompt_parts.append("")

        if past_tweets:
            prompt_parts.append("## 過去の投稿:")
            for t in past_tweets[:5]:
                prompt_parts.append(f"- {t.get('content', '')[:100]}")
            prompt_parts.append("")

        if config:
            themes = config.get("themes", [])
            if themes:
                prompt_parts.append(f"## 使用テーマ: {', '.join(themes)}")

        prompt_parts.append("\n7日分のコンテンツ計画をJSON形式で出力してください。1日2-3投稿を目安に。")

        response = self.run("\n".join(prompt_parts))

        # Parse JSON from response
        try:
            # Extract JSON block if wrapped in markdown
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            else:
                json_str = response
            data = json.loads(json_str.strip())
            return data.get("plans", data if isinstance(data, list) else [])
        except (json.JSONDecodeError, IndexError):
            return [{"day": today, "theme": "AI最新ニュース", "content_type": "single", "description": response[:200], "priority": 3}]
