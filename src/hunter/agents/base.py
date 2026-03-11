"""Base agent class using Claude API."""

import anthropic


class AgentAPIError(Exception):
    """Raised when the agent API call fails."""

    def __init__(self, message: str, is_credit_error: bool = False):
        super().__init__(message)
        self.is_credit_error = is_credit_error


class BaseAgent:
    """Base class for all HUNTER-v2 agents."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.system_prompt = ""
        self.max_tokens = 1024

    def run(self, user_message: str) -> str:
        """Run the agent with a user message and return the response."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=self.system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            return response.content[0].text
        except anthropic.BadRequestError as e:
            msg = str(e)
            is_credit = "credit balance" in msg.lower()
            if is_credit:
                raise AgentAPIError(
                    "Anthropic APIのクレジットが不足しています。\n"
                    "https://console.anthropic.com の Plans & Billing でクレジットを購入してください。",
                    is_credit_error=True,
                ) from e
            raise AgentAPIError(f"API error: {msg}") from e
        except anthropic.AuthenticationError as e:
            raise AgentAPIError(
                "Anthropic APIキーが無効です。.env の ANTHROPIC_API_KEY を確認してください。",
            ) from e

    def run_with_context(self, messages: list[dict]) -> str:
        """Run the agent with full conversation context."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=self.system_prompt,
                messages=messages,
            )
            return response.content[0].text
        except anthropic.BadRequestError as e:
            msg = str(e)
            is_credit = "credit balance" in msg.lower()
            if is_credit:
                raise AgentAPIError(
                    "Anthropic APIのクレジットが不足しています。\n"
                    "https://console.anthropic.com の Plans & Billing でクレジットを購入してください。",
                    is_credit_error=True,
                ) from e
            raise AgentAPIError(f"API error: {msg}") from e
        except anthropic.AuthenticationError as e:
            raise AgentAPIError(
                "Anthropic APIキーが無効です。.env の ANTHROPIC_API_KEY を確認してください。",
            ) from e
