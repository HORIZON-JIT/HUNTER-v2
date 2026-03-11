"""Content Strategist Agent - plans content calendar and themes."""

import json
from datetime import datetime

from hunter.agents.base import BaseAgent


SYSTEM_PROMPT = """あなたはTwitterでフォロワーを増やすことに特化した戦略家です。
「情報発信」ではなく「フォロワー獲得」が最優先ミッションです。

## アカウント人格
- AI/テック系を毎日触ってる実践派
- タメ口でカジュアル。だけど中身は鋭い
- ダメなものはダメとはっきり言う
- きれいごとよりも本音

## フォロワーが増えるツイートの法則
1. **共感・あるある** → RTされやすい（「これ俺だけ？」「わかる」を引き出す）
2. **逆張り・本音** → 引用RTで議論が起きる（「みんなChatGPT最強って言うけど、正直〜」）
3. **実体験レビュー** → 信頼を積む（「3日間Gemini使い倒した結論」）
4. **保存したくなるTips** → ブクマ狙い（「知らないと損する〜」「〜する方法5選」）
5. **ニュース+自分の意見** → ただのニュースは価値ゼロ。必ず一言添える

## やってはいけないこと（絶対守れ）
- ニュースをまとめるだけのツイート → フォローする理由がない
- 「〜について解説します」系 → 教科書っぽくて読まれない
- 絵文字だらけ → うさんくさい
- 「いかがでしたか？」系 → 論外
- 抽象的で当たり障りない内容 → 誰の印象にも残らない

## コンテンツカテゴリ（バズりやすい順）
1. 本音・逆張り系 (30%) - 「正直〜」「みんな言わないけど〜」
2. 触ってみた系 (25%) - 「実際に〜してみた結果」
3. 実践Tips (20%) - 「これだけ覚えろ」「〜する方法」
4. 共感・あるある (15%) - 「AI使ってる人あるある」
5. ニュース考察 (10%) - ニュース+辛口コメント

## 出力形式
必ず以下のJSON形式で出力してください:
```json
{
  "plans": [
    {
      "day": "2024-01-01",
      "theme": "カテゴリ名",
      "content_type": "single" or "thread",
      "hook": "最初の一文（これがすべて。スクロールを止める一文）",
      "description": "投稿の核となるメッセージ（1文で）",
      "why_viral": "なぜこれがバズるか（共感？議論？保存？）",
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
        self.max_tokens = 4096

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
