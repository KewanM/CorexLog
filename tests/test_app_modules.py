from __future__ import annotations

from app.intent_classifier import intent_classifier
from app.text_enhancer import text_enhancer


def test_intent_classifier_uses_title_keyword() -> None:
    result = intent_classifier.classify("goal", "I want to improve my health this year")

    assert result.key == "goal"
    assert result.folder == "goals"
    assert result.detection_method == "title-keyword"


def test_intent_classifier_falls_back_to_content_rules() -> None:
    result = intent_classifier.classify("", "What if we built a better planning dashboard?")

    assert result.key == "idea"
    assert result.detection_method == "content-classification"


def test_text_enhancer_polishes_and_applies_mode() -> None:
    enhanced = text_enhancer.enhance("today was productive", mode="technical", category="task")

    assert enhanced.mode == "technical"
    assert enhanced.text.startswith("Category: Task. Summary: Today was productive.")
