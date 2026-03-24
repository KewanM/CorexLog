from __future__ import annotations

from app.intent_classifier import intent_classifier
from app.text_enhancer import enhance_text, text_enhancer


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
    assert enhanced.text.startswith("Action item:")


def test_enhance_text_rewrites_messy_input_substantially() -> None:
    original = (
        "hi today we did go to the libarary, we did not go for lunch but we had one at home, "
        "I want today to make an upgrade to my app today to allow it for understanding that "
        "I want to wwrite my dairty daily in difrent phhases but I want help to rewrite it"
    )

    enhanced = enhance_text(original, category="diary", mode="diary")

    assert enhanced != original
    assert "library" in enhanced.lower()
    assert "diary entries" in enhanced.lower()
    assert "different phases" in enhanced.lower()
    assert "rewrite" in enhanced.lower()
