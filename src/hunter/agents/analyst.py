"""Engagement Analyst Agent - tracks performance and suggests improvements."""

import json

from hunter.agents.base import BaseAgent


SYSTEM_PROMPT = """あなたはTwitterエンゲージメント分析の専門家です。

## 役割
- 投稿パフォーマンスを分析し、改善提案を行う
- どの種類のコンテンツがよくバズるか、パターンを特定する
- 最適な投稿時間帯を分析する
- フォロワー増加に貢献する要因を特定する

## 分析の観点
1. エンゲージメント率（いいね + RT + リプライ / インプレッション）
2. コンテンツタイプ別パフォーマンス
3. 時間帯別パフォーマンス
4. ハッシュタグの効果
5. フック（最初の一文）の効果

## 出力形式
必ず以下のJSON形式で出力してください:
```json
{
  "summary": "全体のサマリー",
  "top_performing": ["最もパフォーマンスの良かった投稿の特徴"],
  "improvements": ["改善提案のリスト"],
  "recommended_themes": ["おすすめテーマ"],
  "recommended_times": ["おすすめ投稿時間"]
}
```
"""


class AnalystAgent(BaseAgent):
    """Engagement Analyst Agent."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        super().__init__(api_key, model)
        self.system_prompt = SYSTEM_PROMPT
        self.max_tokens = 2048

    def analyze_performance(self, analytics_data: list[dict], tweets: list[dict] | None = None) -> dict:
        """Analyze tweet performance data.

        Args:
            analytics_data: List of analytics records
            tweets: Optional list of tweet content for context

        Returns:
            Analysis report dict
        """
        prompt_parts = ["以下のTwitterパフォーマンスデータを分析してください。\n"]

        prompt_parts.append("## パフォーマンスデータ:")
        for a in analytics_data:
            line = (
                f"- Tweet ID {a.get('tweet_id', '?')}: "
                f"likes={a.get('likes', 0)}, RT={a.get('retweets', 0)}, "
                f"replies={a.get('replies', 0)}, impressions={a.get('impressions', 0)}"
            )
            prompt_parts.append(line)

        if tweets:
            prompt_parts.append("\n## ツイート内容:")
            for t in tweets:
                prompt_parts.append(f"- [{t.get('theme', '')}] {t.get('content', '')[:100]}")

        prompt_parts.append("\n分析結果をJSON形式で出力してください。")

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
            return {"summary": response, "improvements": [], "recommended_themes": [], "recommended_times": []}

    def analyze_competitors(self, competitor_tweets: dict[str, list[dict]]) -> dict:
        """Analyze competitor accounts' tweets.

        Args:
            competitor_tweets: {username: [tweets]} mapping

        Returns:
            Competitor analysis report
        """
        prompt_parts = ["以下の競合アカウントのツイートを分析してください。\n"]

        for username, tweets in competitor_tweets.items():
            prompt_parts.append(f"\n## @{username}:")
            for t in tweets[:5]:
                text = t.get("text", t.get("content", ""))[:150]
                likes = t.get("likes", t.get("favorite_count", "?"))
                prompt_parts.append(f"- ({likes} likes) {text}")

        prompt_parts.append(
            "\n競合の強み、バズるコンテンツパターン、"
            "我々が参考にすべき点をJSON形式で分析してください。"
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
            return {"summary": response, "patterns": [], "recommendations": []}
