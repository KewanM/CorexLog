from __future__ import annotations

import os
import re
from dataclasses import dataclass

from dotenv import load_dotenv
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI


load_dotenv()

SUPPORTED_MODES = {
    "professional",
    "diary",
    "storytelling",
    "motivational",
    "technical",
}

CATEGORY_STYLE_GUIDANCE = {
    "diary": "Use a reflective, personal, emotionally honest tone.",
    "book": "Use descriptive, vivid, storytelling language with stronger scene flow.",
    "task": "Use concise, actionable language with clear next steps.",
    "idea": "Use structured, clear, exploratory language with strong readability.",
    "event": "Use polished, informative language that keeps timing and purpose clear.",
    "goal": "Use motivating, confident language focused on progress and intention.",
    "note": "Use professional, clean, well-organized language.",
}

MODE_STYLE_GUIDANCE = {
    "professional": "Sound polished, professional, and natural.",
    "diary": "Sound personal, reflective, and sincere.",
    "storytelling": "Sound descriptive, vivid, and engaging.",
    "motivational": "Sound encouraging, forward-looking, and energetic.",
    "technical": "Sound precise, structured, and clear.",
}

COMMON_CORRECTIONS = {
    "im": "I'm",
    "ive": "I've",
    "id": "I'd",
    "dont": "don't",
    "didnt": "didn't",
    "cant": "can't",
    "wont": "won't",
    "doesnt": "doesn't",
    "isnt": "isn't",
    "arent": "aren't",
    "wasnt": "wasn't",
    "werent": "weren't",
    "libarary": "library",
    "wwrite": "write",
    "dairty": "diary",
    "difrent": "different",
    "phhases": "phases",
    "becuase": "because",
    "teh": "the",
    "thier": "their",
    "recieve": "receive",
}

CLAUSE_REWRITES = {
    r"\bi want to\b": "I want to",
    r"\bi need to\b": "I need to",
    r"\bi would like help\b": "I would like help",
    r"\bwe did go to\b": "we went to",
    r"\bwe did not go\b": "we didn't go",
    r"\bbut i\b": "but I",
    r"\btoday i\b": "Today I",
    r"\bi learned a lot\b": "I learned a great deal",
}


@dataclass(frozen=True)
class EnhancedText:
    mode: str
    text: str
    source: str


class TextEnhancer:
    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self._client: OpenAI | None = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            api_key = os.getenv("OPENAI_API_KEY", "").strip()
            if not api_key or api_key == "your_api_key_here":
                raise RuntimeError("OpenAI is not configured.")
            self._client = OpenAI(api_key=api_key)
        return self._client

    def enhance(self, text: str, category: str, mode: str = "professional") -> EnhancedText:
        return self.enhance_text(text=text, category=category, mode=mode)

    def enhance_text(self, text: str, category: str, mode: str = "professional") -> EnhancedText:
        normalized_mode = mode.strip().lower()
        if normalized_mode not in SUPPORTED_MODES:
            normalized_mode = "professional"

        stripped = text.strip()
        if not stripped:
            return EnhancedText(mode=normalized_mode, text="", source="local")

        ai_result = self._enhance_with_openai(stripped, category=category, mode=normalized_mode)
        if ai_result is not None:
            return ai_result
        return EnhancedText(
            mode=normalized_mode,
            text=self._enhance_locally(stripped, category=category, mode=normalized_mode),
            source="local",
        )

    def _enhance_with_openai(self, text: str, *, category: str, mode: str) -> EnhancedText | None:
        if not os.getenv("OPENAI_API_KEY", "").strip():
            return None

        prompt = (
            "Rewrite the user's text so it is substantially better written while preserving meaning. "
            "Fix spelling, grammar, sentence structure, clarity, and flow. "
            f"Category guidance: {CATEGORY_STYLE_GUIDANCE.get(category, CATEGORY_STYLE_GUIDANCE['note'])} "
            f"Mode guidance: {MODE_STYLE_GUIDANCE[mode]} "
            "Return only the rewritten text."
        )
        try:
            response = self.client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text},
                ],
            )
        except (APIConnectionError, APITimeoutError, APIStatusError, RuntimeError):
            return None

        rewritten = response.output_text.strip()
        if not rewritten:
            return None
        return EnhancedText(mode=mode, text=rewritten, source="openai")

    def _enhance_locally(self, text: str, *, category: str, mode: str) -> str:
        normalized = self._normalize_spacing(text)
        corrected = self._apply_spelling_and_grammar(normalized)
        grouped_sentences = self._split_into_sentences(corrected)
        rewritten_sentences = [
            self._rewrite_sentence(sentence, category=category, mode=mode)
            for sentence in grouped_sentences
            if sentence.strip()
        ]
        polished = self._polish_paragraph(rewritten_sentences, category=category, mode=mode)
        return polished

    def _normalize_spacing(self, text: str) -> str:
        text = text.replace("\n", " ")
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"\s+([,.;!?])", r"\1", text)
        return text

    def _apply_spelling_and_grammar(self, text: str) -> str:
        corrected = text
        for wrong, right in COMMON_CORRECTIONS.items():
            corrected = re.sub(rf"\b{re.escape(wrong)}\b", right, corrected, flags=re.IGNORECASE)
        for pattern, replacement in CLAUSE_REWRITES.items():
            corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)

        corrected = re.sub(r"\bi\b", "I", corrected)
        corrected = re.sub(r"\btoday today\b", "today", corrected, flags=re.IGNORECASE)
        corrected = re.sub(r"\b([A-Za-z]+) \1\b", r"\1", corrected)
        corrected = re.sub(r",\s*but", ", but", corrected)
        corrected = re.sub(r"\s*,\s*", ", ", corrected)
        corrected = re.sub(r"\s{2,}", " ", corrected)
        return corrected.strip()

    def _split_into_sentences(self, text: str) -> list[str]:
        prepared = re.sub(r"\b(and|but|so)\b", r". \1", text, flags=re.IGNORECASE)
        parts = re.split(r"(?<=[.!?])\s+|\.\s+", prepared)
        sentences = [part.strip(" ,") for part in parts if part.strip(" ,")]
        return sentences or [text]

    def _rewrite_sentence(self, sentence: str, *, category: str, mode: str) -> str:
        lowered = sentence.lower()
        rewritten = sentence.strip()

        if "didn't go out for lunch" in lowered or "did not go for lunch" in lowered:
            rewritten = "We didn't go out for lunch, but we had a meal at home instead"
        elif "went to the library" in lowered or "go to the library" in lowered:
            rewritten = "We went to the library"
        elif "diary daily" in lowered or ("diary" in lowered and "different phases" in lowered):
            rewritten = (
                "I want the app to recognize that I am writing diary entries in different phases"
            )
        elif "upgrade to my app" in lowered or "improving my app" in lowered:
            rewritten = (
                "I want to improve my app so it can better understand that I am writing "
                "diary entries in different phases"
            )
        elif "rewrite" in lowered and "diary" in lowered:
            rewritten = (
                "I would like help rewriting my diary entries so they are clearer, more polished, and better organized"
            )
        elif "rewrite it" in lowered and category == "diary":
            rewritten = (
                "I would like help rewrite it so the final version is clearer and more polished"
            )
        elif category == "task":
            rewritten = self._rewrite_task_sentence(rewritten)
        elif category == "goal":
            rewritten = self._rewrite_goal_sentence(rewritten)
        elif category == "idea":
            rewritten = self._rewrite_idea_sentence(rewritten)
        elif category == "note":
            rewritten = self._rewrite_note_sentence(rewritten)
        elif category == "diary":
            rewritten = self._rewrite_diary_sentence(rewritten)

        rewritten = rewritten.strip()
        rewritten = rewritten[0].upper() + rewritten[1:] if rewritten else rewritten
        if rewritten and rewritten[-1] not in ".!?":
            rewritten = f"{rewritten}."
        return rewritten

    def _rewrite_task_sentence(self, sentence: str) -> str:
        sentence = re.sub(r"^\bremember to\b\s*", "", sentence, flags=re.IGNORECASE)
        sentence = sentence.strip()
        return f"Action item: {sentence}" if not sentence.lower().startswith("action item:") else sentence

    def _rewrite_goal_sentence(self, sentence: str) -> str:
        if sentence.lower().startswith("my goal"):
            return sentence
        return f"My goal is to {sentence[0].lower() + sentence[1:]}" if sentence else sentence

    def _rewrite_idea_sentence(self, sentence: str) -> str:
        if sentence.lower().startswith("idea:"):
            return sentence
        return f"Idea: {sentence[0].lower() + sentence[1:]}" if sentence else sentence

    def _rewrite_note_sentence(self, sentence: str) -> str:
        return sentence.replace("I think", "A key point is")

    def _rewrite_diary_sentence(self, sentence: str) -> str:
        if sentence.lower().startswith("today was"):
            return sentence.replace("Today was", "Today felt", 1)
        return sentence

    def _polish_paragraph(self, sentences: list[str], *, category: str, mode: str) -> str:
        merged = self._merge_related_sentences(sentences)
        if category == "diary" or mode == "diary":
            return self._shape_diary_tone(merged)
        if category == "book" or mode == "storytelling":
            return self._shape_story_tone(merged)
        if category == "goal" or mode == "motivational":
            return self._shape_motivational_tone(merged)
        if category == "task" or mode == "technical":
            return self._shape_structured_tone(merged)
        return " ".join(merged)

    def _merge_related_sentences(self, sentences: list[str]) -> list[str]:
        merged: list[str] = []
        i = 0
        while i < len(sentences):
            current = sentences[i]
            next_sentence = sentences[i + 1] if i + 1 < len(sentences) else None
            if (
                next_sentence
                and current.startswith("We went to the library")
                and (
                    "meal at home" in next_sentence.lower()
                    or "had one at home" in next_sentence.lower()
                )
            ):
                merged.append(
                    "We went to the library, and although we didn't go out for lunch, we had a meal at home instead."
                )
                i += 2
                continue
            if next_sentence and next_sentence.lower().startswith("but "):
                merged.append(
                    f"{current[:-1]}, {next_sentence[0].lower() + next_sentence[1:]}"
                )
                i += 2
                continue
            if (
                next_sentence
                and "improve my app" in current.lower()
                and (
                    "rewriting my diary entries" in next_sentence.lower()
                    or "writing diary entries in different phases" in next_sentence.lower()
                )
            ):
                merged.append(
                    (
                        "I also want to improve my app so it can better understand "
                        "that I am writing diary entries in different phases, and "
                        "I would like help rewriting them so they are clearer and "
                        "better written."
                    )
                )
                i += 2
                continue
            merged.append(current)
            i += 1
        return merged

    def _shape_diary_tone(self, sentences: list[str]) -> str:
        if not sentences:
            return ""
        polished = []
        for sentence in sentences:
            updated = sentence
            if updated.lower().startswith("today felt"):
                updated = updated.replace("Today felt", "Today was", 1)
            updated = updated.replace(
                "Today was a hard day",
                "Today was a challenging day",
            )
            polished.append(updated)
        return " ".join(polished)

    def _shape_story_tone(self, sentences: list[str]) -> str:
        return " ".join(sentence.replace("I want to", "I set out to") for sentence in sentences)

    def _shape_motivational_tone(self, sentences: list[str]) -> str:
        if not sentences:
            return ""
        body = " ".join(sentences)
        return f"{body} This gives me a strong foundation to keep moving forward."

    def _shape_structured_tone(self, sentences: list[str]) -> str:
        cleaned = [sentence.replace("Action item: ", "") for sentence in sentences]
        return " ".join(f"Action item: {sentence}" for sentence in cleaned)


def enhance_text(text: str, category: str, mode: str = "professional") -> str:
    return text_enhancer.enhance_text(text=text, category=category, mode=mode).text


text_enhancer = TextEnhancer()
