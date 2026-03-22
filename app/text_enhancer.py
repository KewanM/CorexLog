from __future__ import annotations

import re
from dataclasses import dataclass


SUPPORTED_MODES = {
    "professional",
    "emotional",
    "motivational",
    "technical",
    "storytelling",
}


@dataclass(frozen=True)
class EnhancedText:
    mode: str
    text: str


class TextEnhancer:
    MODE_PREFIXES = {
        "professional": "",
        "emotional": "Emotionally grounded rewrite: ",
        "motivational": "Motivational rewrite: ",
        "technical": "Structured rewrite: ",
        "storytelling": "Storytelling rewrite: ",
    }

    def enhance(self, text: str, mode: str = "professional", category: str = "note") -> EnhancedText:
        normalized_mode = mode.strip().lower()
        if normalized_mode not in SUPPORTED_MODES:
            normalized_mode = "professional"

        polished = self._polish_text(text)
        transformed = self._apply_mode(polished, normalized_mode, category)
        return EnhancedText(mode=normalized_mode, text=transformed)

    def _polish_text(self, text: str) -> str:
        cleaned = re.sub(r"\s+", " ", text.strip())
        if not cleaned:
            return ""
        sentences = re.split(r"(?<=[.!?])\s+", cleaned)
        polished_sentences = [self._normalize_sentence(sentence) for sentence in sentences if sentence]
        result = " ".join(polished_sentences)
        if result[-1] not in ".!?":
            result = f"{result}."
        return result

    def _normalize_sentence(self, sentence: str) -> str:
        sentence = sentence.strip()
        if not sentence:
            return sentence
        return sentence[0].upper() + sentence[1:]

    def _apply_mode(self, text: str, mode: str, category: str) -> str:
        if mode == "professional":
            return text
        if mode == "emotional":
            return f"I want to capture this honestly: {text}"
        if mode == "motivational":
            return f"Here is a forward-looking version: {text}"
        if mode == "technical":
            return f"Category: {category.title()}. Summary: {text}"
        return f"Scene draft: {text}"


text_enhancer = TextEnhancer()
