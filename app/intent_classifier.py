from __future__ import annotations

from dataclasses import dataclass


CATEGORY_KEYWORDS = {
    "diary": ("diary", "journal", "journaling"),
    "book": ("book", "chapter", "novel", "story"),
    "task": ("task", "todo", "to-do", "reminder"),
    "idea": ("idea", "brainstorm", "concept"),
    "event": ("event", "meeting", "appointment", "schedule"),
    "goal": ("goal", "objective", "target", "plan"),
    "note": ("note", "memo", "summary"),
}

CATEGORY_FOLDERS = {
    "diary": "diary",
    "book": "book",
    "task": "tasks",
    "idea": "ideas",
    "event": "events",
    "goal": "goals",
    "note": "notes",
}

CATEGORY_LABELS = {
    "diary": "Diary",
    "book": "Book",
    "task": "Task",
    "idea": "Idea",
    "event": "Event",
    "goal": "Goal",
    "note": "Note",
}


@dataclass(frozen=True)
class IntentResult:
    key: str
    label: str
    folder: str
    tags: list[str]
    detection_method: str


class IntentClassifier:
    CONTENT_RULES = {
        "diary": ("today i", "i felt", "i learned", "my day", "reflecting"),
        "book": ("chapter", "character", "plot", "scene", "narrative"),
        "task": ("need to", "remember to", "complete", "finish", "submit"),
        "idea": ("what if", "we could", "brainstorm", "proposal", "concept"),
        "event": ("tomorrow", "meeting", "appointment", "at ", "on "),
        "goal": ("goal", "milestone", "achieve", "improve", "target"),
        "note": ("note", "summary", "key point", "important", "remember"),
    }

    def classify(self, title: str, text: str) -> IntentResult:
        title_keyword = self._keyword_match(title)
        if title_keyword is not None:
            return self._build_result(title_keyword, "title-keyword")

        first_line = text.strip().splitlines()[0] if text.strip() else ""
        first_line_keyword = self._keyword_match(first_line)
        if first_line_keyword is not None:
            return self._build_result(first_line_keyword, "first-line-keyword")

        lowered = f"{title} {text}".lower()
        scores = {
            category: sum(1 for phrase in phrases if phrase in lowered)
            for category, phrases in self.CONTENT_RULES.items()
        }
        best_category = max(scores, key=scores.get)
        if scores[best_category] == 0:
            best_category = "note"
        return self._build_result(best_category, "content-classification")

    def _keyword_match(self, value: str) -> str | None:
        normalized = value.strip().lower().rstrip(":")
        for category, keywords in CATEGORY_KEYWORDS.items():
            if normalized in keywords:
                return category
        return None

    def _build_result(self, category: str, detection_method: str) -> IntentResult:
        return IntentResult(
            key=category,
            label=CATEGORY_LABELS[category],
            folder=CATEGORY_FOLDERS[category],
            tags=[category],
            detection_method=detection_method,
        )


intent_classifier = IntentClassifier()
