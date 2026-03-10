"""Content Creator Agent - generates tweet text."""

import json

from hunter.agents.base import BaseAgent


SYSTEM_PROMPT = """あなたはテック/AI分野のTwitterコンテンツクリエイターです。

## 役割
- 与えられたテーマと概要に基づいて、バズるツイートを作成する
- 280文字以内に収める（日本語の場合は140文字以内が理想）
- フック（最初の一文）を強くして、読者の注目を引く

## ツイート作成のルール
1. 最初の一文で興味を引く（驚き、問いかけ、数字を使う）
2. 簡潔で読みやすい文体
3. 具体的な数字や事実を含める
4. 最後にCTA（行動喚起）を入れる（いいね、RT、フォロー促進）
5. 適切なハッシュタグを1-3個含める
6. 絵文字は控えめに使用（0-2個）

## スレッドの場合
- 1ツイート目: フックと全体の概要
- 中間: 具体的な内容（各ツイート280文字以内）
- 最終: まとめとCTA

## 出力形式
必ず以下のJSON形式で出力してください:
```json
{
  "tweets": [
    {
      "text": "ツイート本文",
      "type": "single" or "thread_part",
      "hashtags": ["#AI", "#LLM"]
    }
  ],
  "alternatives": [
    {
      "text": "代替案のツイート本文",
      "hashtags": ["#AI"]
    }
  ]
}
```
"""


class CreatorAgent(BaseAgent):
    """Content Creator Agent."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        super().__init__(api_key, model)
        self.system_prompt = SYSTEM_PROMPT
        self.max_tokens = 2048

    def create_tweet(self, theme: str, description: str, content_type: str = "single") -> dict:
        """Create tweet content based on a plan item.

        Args:
            theme: Content theme
            description: Description of what to write about
            content_type: "single" or "thread"

        Returns:
            {"tweets": [...], "alternatives": [...]}
        """
        if content_type == "thread":
            prompt = (
                f"テーマ: {theme}\n"
                f"内容: {description}\n\n"
                f"上記のテーマでTwitterスレッド（3-5ツイート）を作成してください。\n"
                f"各ツイートは280文字以内にしてください。\n"
                f"代替案も1つ作成してください。"
            )
        else:
            prompt = (
                f"テーマ: {theme}\n"
                f"内容: {description}\n\n"
                f"上記のテーマでツイートを1つ作成してください。280文字以内。\n"
                f"代替案も2つ作成してください。"
            )

        response = self.run(prompt)

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
                "tweets": [{"text": response[:280], "type": "single", "hashtags": []}],
                "alternatives": [],
            }

    def create_from_trend(self, trending_tweet: dict) -> dict:
        """Create a tweet inspired by a trending tweet.

        Args:
            trending_tweet: A tweet dict with 'text', 'likes', etc.

        Returns:
            {"tweets": [...], "alternatives": [...]}
        """
        text = trending_tweet.get("text", trending_tweet.get("content", ""))
        likes = trending_tweet.get("likes", trending_tweet.get("favorite_count", "?"))

        prompt = (
            f"以下のバズったツイートを参考に、独自の視点で新しいツイートを作成してください。\n"
            f"コピーではなく、インスピレーションとして使ってください。\n\n"
            f"参考ツイート（{likes} likes）:\n{text}\n\n"
            f"280文字以内のツイートを1つと、代替案を1つ作成してください。"
        )

        response = self.run(prompt)

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
                "tweets": [{"text": response[:280], "type": "single", "hashtags": []}],
                "alternatives": [],
            }
