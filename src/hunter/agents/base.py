"""Base agent class using Claude API."""

import anthropic


class BaseAgent:
    """Base class for all HUNTER-v2 agents."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.system_prompt = ""
        self.max_tokens = 1024

    def run(self, user_message: str) -> str:
        """Run the agent with a user message and return the response."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text

    def run_with_context(self, messages: list[dict]) -> str:
        """Run the agent with full conversation context."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.system_prompt,
            messages=messages,
        )
        return response.content[0].text
