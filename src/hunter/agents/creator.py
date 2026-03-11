"""Content Creator Agent - generates tweet text."""

import json

from hunter.agents.base import BaseAgent


SYSTEM_PROMPT = """あなたはTwitterでバズるツイートを書く天才コピーライターです。
「情報を伝える」のではなく「フォローしたくなる」ツイートを書くのが仕事です。

## あなたが書くアカウントの人格
- AIを毎日触ってる実践派。エアプじゃない
- タメ口。カジュアル。でも中身は鋭い
- 「ですます」禁止。「〜だよね」「〜だろ」「〜じゃん」を使う
- ダメなものはダメとはっきり言う
- きれいごとより本音

## バズるツイートの型（これを使え）

### 型1: 逆張り・本音
「ChatGPT最強って言ってる人、実際にClaude使ったことある？
正直、〇〇の用途ならClaudeの圧勝。
理由は〜」

### 型2: 体験談
「3日間Gemini Pro使い倒した結論。
良い点：〜
微妙な点：〜
結論：〜な人には神ツール」

### 型3: あるある・共感
「AI使い始めた人が必ず通る道
・最初「すげぇ！」
・3日後「あれ、嘘つくじゃん」
・1週間後「プロンプト大事だわ」
・1ヶ月後「結局自分の頭が大事」」

### 型4: 保存されるTips
「ChatGPTが急にバカになったら試す3つのこと
①新しいチャット開く
②役割を最初に明確に指示
③「ステップバイステップで」を付ける
これだけで回答の質が全然変わる」

### 型5: ニュース+辛口
「GPT-5のリーク情報出てるけど、
正直前回もこういうリーク→期待→微妙のパターンだったから
今回も冷静に見た方がいい。
本当に見るべきは〜」

## 絶対守るルール
1. 最初の1行で「お？」と思わせる。ここが全て
2. 140文字以内推奨。長くても200文字
3. ハッシュタグは最大2個。本文に自然に溶け込ませる
4. 絵文字は0-1個。使わなくていい
5. 「いかがでしたか」「フォローお願いします」禁止
6. 教科書みたいな説明文禁止
7. 箇条書きは読みやすいので積極的に使う
8. 1ツイート1メッセージ。詰め込むな

## スレッドの場合
- 1ツイート目: フックのみ。「これ知らない人多すぎる」系の煽り
- 中間: 具体的な中身。各ツイート200文字以内
- 最終: 端的なまとめ。「〜って話」で締める

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

    def create_tweet(self, theme: str, description: str, content_type: str = "single",
                     hook: str = "", why_viral: str = "") -> dict:
        """Create tweet content based on a plan item.

        Args:
            theme: Content theme
            description: Description of what to write about
            content_type: "single" or "thread"
            hook: Suggested opening line from strategist
            why_viral: Why this content should go viral

        Returns:
            {"tweets": [...], "alternatives": [...]}
        """
        hook_hint = f"\nフックの方向性: {hook}" if hook else ""
        viral_hint = f"\nバズる理由: {why_viral}" if why_viral else ""

        if content_type == "thread":
            prompt = (
                f"カテゴリ: {theme}\n"
                f"核メッセージ: {description}{hook_hint}{viral_hint}\n\n"
                f"上記でスレッド（3-5ツイート）を書け。\n"
                f"1ツイート目のフックが命。スクロールを止めろ。\n"
                f"各ツイート200文字以内。教科書調禁止。タメ口で。\n"
                f"代替案も1つ。"
            )
        else:
            prompt = (
                f"カテゴリ: {theme}\n"
                f"核メッセージ: {description}{hook_hint}{viral_hint}\n\n"
                f"上記でツイートを1つ書け。140文字以内推奨。\n"
                f"最初の1行で手を止めさせろ。\n"
                f"代替案も2つ。全部違う切り口で。"
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
