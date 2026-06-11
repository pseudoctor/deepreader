"""LLM provider boundary for future AI coach integrations."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Literal
from urllib import error, request

ProviderName = Literal["mock", "openai", "claude", "gemini", "deepseek", "qwen"]
JSON_OBJECT_INSTRUCTIONS = (
    "Return only valid JSON matching this schema. Do not wrap the JSON in Markdown.\n\n"
)


@dataclass(frozen=True)
class LLMProviderSpec:
    name: ProviderName
    display_name: str
    api_key_env: str | None
    default_base_url: str | None
    model_env: str
    default_model: str

    @property
    def base_url_env(self) -> str:
        return f"DEEP_READING_{self.name.upper()}_BASE_URL"


PROVIDER_SPECS: tuple[LLMProviderSpec, ...] = (
    LLMProviderSpec(
        name="mock",
        display_name="Local Mock",
        api_key_env=None,
        default_base_url=None,
        model_env="DEEP_READING_MOCK_MODEL",
        default_model="mock-local",
    ),
    LLMProviderSpec(
        name="openai",
        display_name="OpenAI",
        api_key_env="OPENAI_API_KEY",
        default_base_url="https://api.openai.com/v1",
        model_env="OPENAI_MODEL",
        default_model="gpt-4.1-mini",
    ),
    LLMProviderSpec(
        name="claude",
        display_name="Claude",
        api_key_env="ANTHROPIC_API_KEY",
        default_base_url="https://api.anthropic.com/v1",
        model_env="ANTHROPIC_MODEL",
        default_model="claude-3-5-sonnet-latest",
    ),
    LLMProviderSpec(
        name="gemini",
        display_name="Gemini",
        api_key_env="GEMINI_API_KEY",
        default_base_url="https://generativelanguage.googleapis.com/v1beta",
        model_env="GEMINI_MODEL",
        default_model="gemini-1.5-pro",
    ),
    LLMProviderSpec(
        name="deepseek",
        display_name="DeepSeek",
        api_key_env="DEEPSEEK_API_KEY",
        default_base_url="https://api.deepseek.com",
        model_env="DEEPSEEK_MODEL",
        default_model="deepseek-chat",
    ),
    LLMProviderSpec(
        name="qwen",
        display_name="Qwen",
        api_key_env="QWEN_API_KEY",
        default_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model_env="QWEN_MODEL",
        default_model="qwen-plus",
    ),
)

PROVIDER_NAMES = {spec.name for spec in PROVIDER_SPECS}
DEFAULT_PROVIDER: ProviderName = "mock"
CAUSAL_MARKERS = (
    "because",
    "therefore",
    "so",
    "since",
    "leads to",
    "causes",
    "因",
    "所以",
    "导致",
)
EVIDENCE_MARKERS = (
    "evidence",
    "example",
    "for example",
    "according",
    "quote",
    "原文",
    "证据",
    "例如",
)
VAGUE_MARKERS = ("things", "stuff", "important", "interesting", "很多", "一些", "重要", "有趣")
REQUEST_TIMEOUT_SECONDS = 60

JSON_SCHEMAS: dict[str, dict[str, object]] = {
    "feynman_check": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "accurate_points": {"type": "array", "items": {"type": "string"}},
            "vague_points": {"type": "array", "items": {"type": "string"}},
            "missing_causal_links": {"type": "array", "items": {"type": "string"}},
            "unsupported_leaps": {"type": "array", "items": {"type": "string"}},
            "rewritten_version": {"type": "string"},
        },
        "required": [
            "accurate_points",
            "vague_points",
            "missing_causal_links",
            "unsupported_leaps",
            "rewritten_version",
        ],
    },
    "selection_explanation": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "explanation": {"type": "string"},
        },
        "required": ["explanation"],
    },
    "selection_review_question": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "question": {"type": "string"},
            "answer": {"type": "string"},
        },
        "required": ["question", "answer"],
    },
}


def provider_spec(name: str) -> LLMProviderSpec:
    normalized = name.strip().lower()
    for spec in PROVIDER_SPECS:
        if spec.name == normalized:
            return spec
    raise ValueError(f"Unsupported LLM provider: {name}")


def configured_provider_name() -> ProviderName:
    value = os.environ.get("DEEP_READING_LLM_PROVIDER", DEFAULT_PROVIDER).strip().lower()
    if value in PROVIDER_NAMES:
        return value  # type: ignore[return-value]
    return DEFAULT_PROVIDER


def set_configured_provider_name(name: str) -> ProviderName:
    spec = provider_spec(name)
    os.environ["DEEP_READING_LLM_PROVIDER"] = spec.name
    return spec.name


def is_configured(spec: LLMProviderSpec) -> bool:
    return spec.api_key_env is None or bool(os.environ.get(spec.api_key_env, "").strip())


def provider_status(spec: LLMProviderSpec) -> dict[str, object]:
    return {
        "name": spec.name,
        "display_name": spec.display_name,
        "configured": is_configured(spec),
        "api_key_env": spec.api_key_env,
        "api_key_present": is_configured(spec),
        "base_url_env": spec.base_url_env,
        "base_url": os.environ.get(spec.base_url_env, spec.default_base_url),
        "model_env": spec.model_env,
        "model": os.environ.get(spec.model_env, spec.default_model),
        "selected_env": "DEEP_READING_LLM_PROVIDER",
    }


def list_provider_status() -> dict[str, object]:
    selected = configured_provider_name()
    return {
        "selected": selected,
        "providers": [provider_status(spec) for spec in PROVIDER_SPECS],
    }


def split_summary_sentences(summary: str) -> list[str]:
    normalized = summary.replace("。", ".").replace("？", "?").replace("！", "!")
    sentences = []
    for chunk in normalized.replace("?", ".").replace("!", ".").split("."):
        sentence = chunk.strip()
        if sentence:
            sentences.append(sentence)
    return sentences


def contains_marker(text: str, marker: str) -> bool:
    if marker.isascii():
        return re.search(rf"\b{re.escape(marker)}\b", text) is not None
    return marker in text


def contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def env_value(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or None


def provider_model(spec: LLMProviderSpec) -> str:
    return env_value(spec.model_env) or spec.default_model


def provider_base_url(spec: LLMProviderSpec) -> str:
    value = env_value(spec.base_url_env) or spec.default_base_url
    if value is None:
        raise RuntimeError(f"{spec.display_name} provider has no base URL configured.")
    return value.rstrip("/")


def response_text(data: dict[str, object]) -> str:
    output_text = data.get("output_text")
    if isinstance(output_text, str):
        return output_text

    chunks: list[str] = []
    output = data.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for content_item in content:
                if not isinstance(content_item, dict):
                    continue
                if content_item.get("type") not in {"output_text", "text"}:
                    continue
                text = content_item.get("text")
                if isinstance(text, str):
                    chunks.append(text)
    return "\n".join(chunks)


def json_schema_payload(schema_name: str) -> dict[str, object]:
    try:
        schema = JSON_SCHEMAS[schema_name]
    except KeyError as exc:
        raise ValueError(f"Unsupported JSON schema: {schema_name}") from exc
    return {
        "type": "json_schema",
        "name": schema_name,
        "schema": schema,
        "strict": True,
    }


def provider_error_message(exc: error.HTTPError) -> str:
    raw_body = exc.read().decode("utf-8", errors="replace")
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return raw_body[:240] if raw_body else exc.reason

    if isinstance(payload, dict):
        error_payload = payload.get("error")
        if isinstance(error_payload, dict):
            message = error_payload.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()
        message = payload.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()
    return raw_body[:240] if raw_body else exc.reason


def post_json(
    spec: LLMProviderSpec,
    endpoint: str,
    payload: dict[str, object],
    headers: dict[str, str],
) -> dict[str, object]:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        message = provider_error_message(exc)
        raise RuntimeError(
            f"{spec.display_name} request failed with status {exc.code}: {message}"
        ) from exc
    except (error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"{spec.display_name} request failed: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{spec.display_name} response was not valid JSON.") from exc

    if not isinstance(data, dict):
        raise RuntimeError(f"{spec.display_name} response was not a JSON object.")
    return data


def parse_json_text(spec: LLMProviderSpec, text: str) -> dict[str, object]:
    if not text.strip():
        raise RuntimeError(f"{spec.display_name} response did not include output text.")
    try:
        result = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{spec.display_name} output text was not valid JSON.") from exc
    if not isinstance(result, dict):
        raise RuntimeError(f"{spec.display_name} output JSON was not an object.")
    return result


def require_api_key(spec: LLMProviderSpec) -> str:
    if spec.api_key_env is None:
        raise RuntimeError(f"{spec.display_name} provider has no API key environment configured.")
    api_key = env_value(spec.api_key_env)
    if api_key is None:
        raise RuntimeError(f"{spec.display_name} API key missing. Set {spec.api_key_env}.")
    return api_key


def schema_prompt(prompt: str, schema_name: str) -> str:
    return (
        JSON_OBJECT_INSTRUCTIONS
        + f"Schema name: {schema_name}\nSchema: "
        + json.dumps(JSON_SCHEMAS[schema_name])
        + "\n\n"
        + prompt
    )


def chat_completion_text(data: dict[str, object]) -> str:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return ""
    message = first_choice.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    return content if isinstance(content, str) else ""


def gemini_text(data: dict[str, object]) -> str:
    candidates = data.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return ""
    first_candidate = candidates[0]
    if not isinstance(first_candidate, dict):
        return ""
    content = first_candidate.get("content")
    if not isinstance(content, dict):
        return ""
    parts = content.get("parts")
    if not isinstance(parts, list):
        return ""
    chunks = [part.get("text") for part in parts if isinstance(part, dict)]
    return "\n".join(chunk for chunk in chunks if isinstance(chunk, str))


class LLMProvider:
    """Minimal provider contract; concrete network clients will implement this later."""

    def __init__(self, spec: LLMProviderSpec) -> None:
        self.spec = spec

    def complete_json(self, _prompt: str, _schema_name: str) -> dict[str, object]:
        raise NotImplementedError

    def check_feynman_summary(
        self,
        chapter: dict[str, object],
        summary: str,
    ) -> dict[str, object]:
        return self.complete_json(
            f"Check this chapter summary for {chapter['id']}: {chapter['title']}\n\n{summary}",
            "feynman_check",
        )

    def explain_selection(
        self,
        chapter: dict[str, object],
        selected_text: str,
    ) -> dict[str, str]:
        result = self.complete_json(
            f"Explain this selected passage from {chapter['id']}: {chapter['title']}\n\n"
            f"{selected_text}",
            "selection_explanation",
        )
        return {key: str(value) for key, value in result.items()}

    def generate_selection_review_question(
        self,
        chapter: dict[str, object],
        selected_text: str,
    ) -> dict[str, str]:
        result = self.complete_json(
            f"Generate a review card for {chapter['id']}: {chapter['title']}\n\n{selected_text}",
            "selection_review_question",
        )
        return {key: str(value) for key, value in result.items()}


class MockLLMProvider(LLMProvider):
    def complete_json(self, prompt: str, schema_name: str) -> dict[str, object]:
        return {
            "provider": self.spec.name,
            "schema": schema_name,
            "content": prompt,
        }

    def check_feynman_summary(
        self,
        chapter: dict[str, object],
        summary: str,
    ) -> dict[str, object]:
        stripped = summary.strip()
        if not stripped:
            raise ValueError("Summary cannot be empty")

        lowered = stripped.casefold()
        sentences = split_summary_sentences(stripped)
        accurate_points = [
            sentence
            for sentence in sentences
            if len(sentence) >= 40
            and not any(contains_marker(sentence.casefold(), marker) for marker in VAGUE_MARKERS)
        ]
        vague_points = [
            sentence
            for sentence in sentences
            if len(sentence) < 40
            or any(contains_marker(sentence.casefold(), marker) for marker in VAGUE_MARKERS)
        ]
        missing_causal_links = []
        if not any(contains_marker(lowered, marker) for marker in CAUSAL_MARKERS):
            missing_causal_links.append(
                "The summary does not clearly explain the causal link or mechanism."
            )

        unsupported_leaps = []
        if not any(contains_marker(lowered, marker) for marker in EVIDENCE_MARKERS):
            unsupported_leaps.append("The summary does not name a concrete example or evidence.")

        rewritten_version = (
            f"In {chapter['id']}: {chapter['title']}, the chapter appears to argue that "
            f"{sentences[0] if sentences else stripped}. To make the explanation stronger, add the "
            "causal mechanism and one concrete piece of evidence from the text."
        )
        return {
            "chapter_id": chapter["id"],
            "title": chapter["title"],
            "accurate_points": accurate_points,
            "vague_points": vague_points,
            "missing_causal_links": missing_causal_links,
            "unsupported_leaps": unsupported_leaps,
            "rewritten_version": rewritten_version,
        }

    def explain_selection(
        self,
        chapter: dict[str, object],
        selected_text: str,
    ) -> dict[str, str]:
        text = selected_text.strip()
        if not text:
            raise ValueError("Selected text cannot be empty")

        if contains_cjk(text):
            explanation = "\n".join(
                [
                    f"选中文段来自 {chapter['id']}: {chapter['title']}",
                    "",
                    "它在说什么：",
                    text,
                    "",
                    "怎么读这段：",
                    (
                        "先判断这段支持了什么主张，再找它给出的证据，以及暗含的因果链。"
                        "如果它在做比较，就追问：被比较对象之间变了什么，什么又保持不变。"
                    ),
                ]
            )
        else:
            explanation = "\n".join(
                [
                    f"Selected passage from {chapter['id']}: {chapter['title']}",
                    "",
                    "What it says:",
                    text,
                    "",
                    "How to read it:",
                    (
                        "Identify the claim this passage supports, the evidence it names, and any "
                        "causal link it implies. If the passage uses a comparison, ask what "
                        "changed between the compared cases and what stays constant."
                    ),
                ]
            )

        return {
            "chapter_id": str(chapter["id"]),
            "title": str(chapter["title"]),
            "explanation": explanation,
        }

    def generate_selection_review_question(
        self,
        chapter: dict[str, object],
        selected_text: str,
    ) -> dict[str, str]:
        text = selected_text.strip()
        if not text:
            raise ValueError("Selected text cannot be empty")

        preview = text if len(text) <= 180 else text[:177].rstrip() + "..."
        if contains_cjk(text):
            return {
                "chapter_id": str(chapter["id"]),
                "title": str(chapter["title"]),
                "question": f"这段文字在 {chapter['id']} 中支持了什么主张或因果链？",
                "answer": (
                    f"可用这段作为证据：{preview}\n\n"
                    "一个好的回答需要说清楚主张、解释因果链，并指出这段本身还不能证明什么。"
                ),
            }

        return {
            "chapter_id": str(chapter["id"]),
            "title": str(chapter["title"]),
            "question": f"What claim or causal link does this passage support in {chapter['id']}?",
            "answer": (
                f"Use this passage as evidence: {preview}\n\n"
                "A strong answer should name the claim, explain the causal link, and state what "
                "the passage does not prove by itself."
            ),
        }


class OpenAIProvider(LLMProvider):
    def complete_json(self, prompt: str, schema_name: str) -> dict[str, object]:
        api_key = require_api_key(self.spec)
        payload = {
            "model": provider_model(self.spec),
            "input": [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "You are a local-first deep reading coach. "
                                "Return only JSON matching the provided schema."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": prompt}],
                },
            ],
            "text": {"format": json_schema_payload(schema_name)},
        }
        data = post_json(
            self.spec,
            f"{provider_base_url(self.spec)}/responses",
            payload,
            {"Authorization": f"Bearer {api_key}"},
        )
        return parse_json_text(self.spec, response_text(data))

    def check_feynman_summary(
        self,
        chapter: dict[str, object],
        summary: str,
    ) -> dict[str, object]:
        stripped = summary.strip()
        if not stripped:
            raise ValueError("Summary cannot be empty")

        result = self.complete_json(
            (
                f"Chapter id: {chapter['id']}\n"
                f"Chapter title: {chapter['title']}\n\n"
                "Check this Feynman-style summary for accuracy, vagueness, missing causal "
                "links, unsupported leaps, and then rewrite it more clearly.\n\n"
                f"Summary:\n{stripped}"
            ),
            "feynman_check",
        )
        return {
            "chapter_id": chapter["id"],
            "title": chapter["title"],
            **result,
        }

    def explain_selection(
        self,
        chapter: dict[str, object],
        selected_text: str,
    ) -> dict[str, str]:
        text = selected_text.strip()
        if not text:
            raise ValueError("Selected text cannot be empty")

        result = self.complete_json(
            (
                f"Chapter id: {chapter['id']}\n"
                f"Chapter title: {chapter['title']}\n\n"
                "Explain the selected passage for a deep-reading learner. Focus on claim, "
                "evidence, causal link, and how to read it.\n\n"
                f"Selected passage:\n{text}"
            ),
            "selection_explanation",
        )
        return {
            "chapter_id": str(chapter["id"]),
            "title": str(chapter["title"]),
            "explanation": str(result["explanation"]),
        }

    def generate_selection_review_question(
        self,
        chapter: dict[str, object],
        selected_text: str,
    ) -> dict[str, str]:
        text = selected_text.strip()
        if not text:
            raise ValueError("Selected text cannot be empty")

        result = self.complete_json(
            (
                f"Chapter id: {chapter['id']}\n"
                f"Chapter title: {chapter['title']}\n\n"
                "Generate one review question and one concise answer for this selected passage. "
                "The question should test the passage's claim, evidence, or causal link.\n\n"
                f"Selected passage:\n{text}"
            ),
            "selection_review_question",
        )
        return {
            "chapter_id": str(chapter["id"]),
            "title": str(chapter["title"]),
            "question": str(result["question"]),
            "answer": str(result["answer"]),
        }


class ChatCompletionsProvider(OpenAIProvider):
    def complete_json(self, prompt: str, schema_name: str) -> dict[str, object]:
        api_key = require_api_key(self.spec)
        payload = {
            "model": provider_model(self.spec),
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a local-first deep reading coach. Return only valid JSON."
                    ),
                },
                {"role": "user", "content": schema_prompt(prompt, schema_name)},
            ],
            "response_format": {"type": "json_object"},
        }
        data = post_json(
            self.spec,
            f"{provider_base_url(self.spec)}/chat/completions",
            payload,
            {"Authorization": f"Bearer {api_key}"},
        )
        return parse_json_text(self.spec, chat_completion_text(data))


class ClaudeProvider(OpenAIProvider):
    def complete_json(self, prompt: str, schema_name: str) -> dict[str, object]:
        api_key = require_api_key(self.spec)
        payload = {
            "model": provider_model(self.spec),
            "max_tokens": 2048,
            "tools": [
                {
                    "name": "return_json",
                    "description": "Return the deep-reading coach result as structured JSON.",
                    "input_schema": JSON_SCHEMAS[schema_name],
                }
            ],
            "tool_choice": {"type": "tool", "name": "return_json"},
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        }
        data = post_json(
            self.spec,
            f"{provider_base_url(self.spec)}/messages",
            payload,
            {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        content = data.get("content")
        if isinstance(content, list):
            for item in content:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "tool_use" and item.get("name") == "return_json":
                    tool_input = item.get("input")
                    if isinstance(tool_input, dict):
                        return tool_input
                if item.get("type") == "text" and isinstance(item.get("text"), str):
                    return parse_json_text(self.spec, str(item["text"]))
        raise RuntimeError("Claude response did not include structured JSON.")


class GeminiProvider(OpenAIProvider):
    def complete_json(self, prompt: str, schema_name: str) -> dict[str, object]:
        api_key = require_api_key(self.spec)
        model = provider_model(self.spec)
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": (
                                "You are a local-first deep reading coach.\n\n"
                                + schema_prompt(prompt, schema_name)
                            )
                        }
                    ],
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "response_json_schema": JSON_SCHEMAS[schema_name],
            },
        }
        data = post_json(
            self.spec,
            f"{provider_base_url(self.spec)}/models/{model}:generateContent",
            payload,
            {"x-goog-api-key": api_key},
        )
        return parse_json_text(self.spec, gemini_text(data))


def build_provider(name: str | None = None) -> LLMProvider:
    spec = provider_spec(name or configured_provider_name())
    if spec.name == "mock":
        return MockLLMProvider(spec)
    if spec.name == "openai":
        return OpenAIProvider(spec)
    if spec.name == "claude":
        return ClaudeProvider(spec)
    if spec.name == "gemini":
        return GeminiProvider(spec)
    if spec.name in {"deepseek", "qwen"}:
        return ChatCompletionsProvider(spec)
    raise ValueError(f"Unsupported LLM provider: {spec.name}")
