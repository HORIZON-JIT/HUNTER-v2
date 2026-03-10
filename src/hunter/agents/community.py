"""Community Manager Agent - engagement and community building strategies."""

import json

from hunter.agents.base import BaseAgent


SYSTEM_PROMPT = """あなたはTwitterコミュニティマネージャーです。

## 役割
- エンゲージメント戦略を立案する
- リプライの候補テキストを生成する
- フォローすべきアカウントを提案する
- 引用RTの候補を見つける
- コラボレーション機会を発見する

## エンゲージメント戦略
1. 価値あるリプライで関係構築
2. 引用RTで自分の視点を追加
3. 業界リーダーとの接点作り
4. コミュニティへの積極参加
5. 定期的なQ&A・議論の場の提供

## 出力形式
必ず以下のJSON形式で出力してください:
```json
{
  "reply_suggestions": [
    {
      "target_tweet": "対象ツイートの概要",
      "reply_text": "リプライ案",
      "purpose": "関係構築 / 専門性アピール / etc"
    }
  ],
  "quote_rt_ideas": [
    {
      "original": "元ツイートの概要",
      "quote_text": "引用RTのテキスト案"
    }
  ],
  "accounts_to_follow": ["おすすめアカウント"],
  "engagement_tips": ["エンゲージメント向上のTips"]
}
```
"""


class CommunityAgent(BaseAgent):
    """Community Manager Agent."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        super().__init__(api_key, model)
        self.system_prompt = SYSTEM_PROMPT
        self.max_tokens = 2048

    def suggest_engagement(self, trending_tweets: list[dict], niche: str = "tech_ai") -> dict:
        """Suggest engagement actions based on trending tweets.

        Args:
            trending_tweets: List of trending tweets in the niche
            niche: Content niche

        Returns:
            Engagement suggestions dict
        """
        prompt_parts = [
            f"ジャンル: {niche}\n",
            "以下のトレンドツイートに対するエンゲージメント戦略を提案してください。\n",
        ]

        for t in trending_tweets[:10]:
            text = t.get("text", t.get("content", ""))[:200]
            user = t.get("user", {}).get("screen_name", t.get("username", "unknown"))
            likes = t.get("likes", t.get("favorite_count", "?"))
            prompt_parts.append(f"- @{user} ({likes} likes): {text}")

        prompt_parts.append(
            "\nリプライ案、引用RT案、フォローすべきアカウント、"
            "エンゲージメントTipsをJSON形式で出力してください。"
        )

        response = self.run("\n".join(prompt_parts))

        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            else:
                json_str = response
            return json.loads(json_str.strip())
        except (json.JSONDecodeError, IndexError):
            return {
                "reply_suggestions": [],
                "quote_rt_ideas": [],
                "accounts_to_follow": [],
                "engagement_tips": [response[:500]],
            }

    def generate_replies(self, tweets: list[dict]) -> list[dict]:
        """Generate reply suggestions for specific tweets.

        Args:
            tweets: List of tweets to reply to

        Returns:
            List of reply suggestions
        """
        prompt_parts = ["以下のツイートに対する、価値あるリプライ案を作成してください。\n"]

        for t in tweets[:5]:
            text = t.get("text", t.get("content", ""))[:200]
            user = t.get("user", {}).get("screen_name", t.get("username", "unknown"))
            prompt_parts.append(f"- @{user}: {text}")

        prompt_parts.append(
            "\n各ツイートに対して、専門性を示しつつ親しみやすいリプライを1-2案ずつ作成してください。"
            "JSON形式で出力してください。"
        )

        response = self.run("\n".join(prompt_parts))

        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            else:
                json_str = response
            return json.loads(json_str.strip()) if isinstance(json.loads(json_str.strip()), list) else []
        except (json.JSONDecodeError, IndexError):
            return []
