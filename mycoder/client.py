"""Ollama API client with streaming and tool support."""

import json
import requests
from dataclasses import dataclass, field

OLLAMA_BASE = "http://localhost:11434"


@dataclass
class Metrics:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    prompt_eval_duration: float = 0
    eval_duration: float = 0
    total_duration: float = 0
    load_duration: float = 0

    @property
    def total_tokens(self):
        return self.prompt_tokens + self.completion_tokens

    @property
    def tokens_per_second(self):
        if self.eval_duration > 0:
            return self.completion_tokens / self.eval_duration
        return 0.0

    @property
    def prompt_tokens_per_second(self):
        if self.prompt_eval_duration > 0:
            return self.prompt_tokens / self.prompt_eval_duration
        return 0.0


@dataclass
class ChatResponse:
    content: str = ""
    thinking: str = ""
    tool_calls: list = field(default_factory=list)
    metrics: Metrics = field(default_factory=Metrics)


class OllamaClient:
    def __init__(self, base_url=OLLAMA_BASE):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def is_running(self):
        try:
            self.session.get(f"{self.base_url}/api/tags", timeout=3)
            return True
        except (requests.ConnectionError, requests.Timeout):
            return False

    def list_models(self):
        resp = self.session.get(f"{self.base_url}/api/tags")
        resp.raise_for_status()
        models = resp.json().get("models", [])
        return [m for m in models if "embed" not in m.get("name", "").lower()]

    def all_models(self):
        resp = self.session.get(f"{self.base_url}/api/tags")
        resp.raise_for_status()
        return resp.json().get("models", [])

    def show_model(self, name):
        resp = self.session.post(f"{self.base_url}/api/show", json={"name": name})
        resp.raise_for_status()
        return resp.json()

    def running_models(self):
        try:
            resp = self.session.get(f"{self.base_url}/api/ps")
            resp.raise_for_status()
            return resp.json().get("models", [])
        except Exception:
            return []

    def chat_stream(self, model, messages, tools=None, options=None,
                    on_token=None, on_thinking=None):
        payload = {"model": model, "messages": messages, "stream": True}
        if tools:
            payload["tools"] = tools
        if options:
            payload["options"] = options

        response = ChatResponse()

        with self.session.post(
            f"{self.base_url}/api/chat",
            json=payload,
            stream=True,
            timeout=(10, 600),
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                data = json.loads(line)

                if "message" in data:
                    msg = data["message"]

                    token = msg.get("content", "")
                    if token:
                        if on_token:
                            on_token(token)
                        response.content += token

                    thinking = msg.get("thinking", "")
                    if thinking:
                        if on_thinking:
                            on_thinking(thinking)
                        response.thinking += thinking

                    if msg.get("tool_calls"):
                        response.tool_calls = msg["tool_calls"]

                if data.get("done"):
                    response.metrics = Metrics(
                        prompt_tokens=data.get("prompt_eval_count", 0),
                        completion_tokens=data.get("eval_count", 0),
                        prompt_eval_duration=data.get("prompt_eval_duration", 0) / 1e9,
                        eval_duration=data.get("eval_duration", 0) / 1e9,
                        total_duration=data.get("total_duration", 0) / 1e9,
                        load_duration=data.get("load_duration", 0) / 1e9,
                    )

        return response
