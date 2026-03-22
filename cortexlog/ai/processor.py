from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from dotenv import load_dotenv
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from cortexlog.db.database import database_manager
from cortexlog.db.models import AI_DATETIME_FORMAT, serialize_datetime
from cortexlog.services.events_service import events_service
from cortexlog.services.notes_service import notes_service
from cortexlog.services.tasks_service import tasks_service
from cortexlog.utils.datetime_parser import parse_ai_datetime


LOGGER = logging.getLogger(__name__)
load_dotenv()


SYSTEM_PROMPT = """
You extract structured personal information from free-form user text.
Return JSON only.

Required JSON schema:
{{
  "notes": [{{"content": "string"}}],
  "tasks": [{{"content": "string", "due_date": "YYYY-MM-DD HH:MM"}}],
  "events": [{{"title": "string", "event_time": "YYYY-MM-DD HH:MM"}}]
}}

Rules:
- Always return the exact top-level keys: notes, tasks, events.
- Use empty arrays when no items are present.
- Convert relative dates and times into explicit datetimes.
- The current local datetime is: {current_datetime}
- If a task has no due date, set due_date to null.
- If an event time cannot be determined precisely, do not create the event.
- Notes should capture informational statements, ideas, journal-style content, or reference text.
- Do not include explanations, markdown, or extra keys.
""".strip()


RESPONSE_SCHEMA = {
    "name": "cortexlog_extraction",
    "schema": {
        "type": "object",
        "properties": {
            "notes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"content": {"type": "string"}},
                    "required": ["content"],
                    "additionalProperties": False,
                },
            },
            "tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string"},
                        "due_date": {"type": ["string", "null"]},
                    },
                    "required": ["content", "due_date"],
                    "additionalProperties": False,
                },
            },
            "events": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "event_time": {"type": "string"},
                    },
                    "required": ["title", "event_time"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["notes", "tasks", "events"],
        "additionalProperties": False,
    },
    "strict": True,
}


@dataclass
class ParsedLog:
    notes: list[dict[str, Any]]
    tasks: list[dict[str, Any]]
    events: list[dict[str, Any]]
    source: str = "openai"

    def to_json(self) -> str:
        return json.dumps(
            {"notes": self.notes, "tasks": self.tasks, "events": self.events},
            ensure_ascii=True,
        )


class AIValidationError(ValueError):
    pass


class AIProcessor:
    WEEKDAY_INDEX = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    TASK_PREFIXES = (
        "buy",
        "call",
        "email",
        "finish",
        "pay",
        "submit",
        "send",
        "schedule",
        "pick up",
        "remember to",
        "need to",
        "remind me to",
        "don't forget to",
        "todo",
        "to do",
        "task",
    )

    EVENT_MARKERS = (
        "meeting",
        "appointment",
        "birthday",
        "dinner",
        "lunch",
        "breakfast",
        "event",
        "party",
        "interview",
        "flight",
        "doctor",
        "dentist",
    )

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self._client: OpenAI | None = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            api_key = os.getenv("OPENAI_API_KEY", "").strip()
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY is not set in the environment.")
            if api_key == "your_api_key_here":
                raise RuntimeError(
                    "OPENAI_API_KEY is still set to the placeholder value in .env. "
                    "Replace it with your real OpenAI API key."
                )
            self._client = OpenAI(api_key=api_key)
        return self._client

    def process_text(self, raw_text: str) -> ParsedLog:
        try:
            response = self.client.responses.create(
                model=self.model,
                input=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT.format(
                            current_datetime=datetime.now().strftime(AI_DATETIME_FORMAT)
                        ),
                    },
                    {"role": "user", "content": raw_text},
                ],
                text={"format": {"type": "json_schema", **RESPONSE_SCHEMA}},
            )
        except APIConnectionError as exc:
            if self._require_openai():
                raise RuntimeError(
                    "OpenAI processing is required, but the API could not be reached."
                ) from exc
            LOGGER.warning("OpenAI API connection failed; falling back to local parsing.")
            return self._persist_fallback(raw_text)
        except APITimeoutError as exc:
            if self._require_openai():
                raise RuntimeError(
                    "OpenAI processing is required, but the API request timed out."
                ) from exc
            LOGGER.warning("OpenAI API timed out; falling back to local parsing.")
            return self._persist_fallback(raw_text)
        except APIStatusError as exc:
            if exc.status_code == 401:
                raise RuntimeError(
                    "OpenAI rejected the API key (401 Unauthorized). "
                    "Check OPENAI_API_KEY in .env and make sure it is a real, active key."
                ) from exc
            if exc.status_code == 429:
                if self._require_openai():
                    raise RuntimeError(
                        "OpenAI processing is required, but the API returned 429 Too Many Requests. "
                        "Check your quota or billing."
                    ) from exc
                LOGGER.warning("OpenAI API quota/rate limit hit; falling back to local parsing.")
                return self._persist_fallback(raw_text)
            raise RuntimeError(
                f"OpenAI API returned an error ({exc.status_code}). Please try again."
            ) from exc
        raw_output = response.output_text
        parsed = self.validate_json(raw_output)
        self.store_raw_log(raw_text=raw_text, ai_json=parsed.to_json())
        self.persist_items(parsed)
        return parsed

    def _require_openai(self) -> bool:
        value = os.getenv("CORTEXLOG_REQUIRE_OPENAI", "").strip().lower()
        return value in {"1", "true", "yes", "on"}

    def _persist_fallback(self, raw_text: str) -> ParsedLog:
        parsed = self.local_fallback_parse(raw_text)
        self.store_raw_log(raw_text=raw_text, ai_json=parsed.to_json())
        self.persist_items(parsed)
        return parsed

    def local_fallback_parse(self, raw_text: str) -> ParsedLog:
        text = raw_text.strip()
        if not text:
            raise AIValidationError("Entry cannot be empty.")

        due_date = self._extract_due_date(text)
        event_time = self._extract_event_time(text)

        if event_time is not None and self._looks_like_event(text):
            title = self._clean_content(text)
            return ParsedLog(
                notes=[],
                tasks=[],
                events=[{"title": title, "event_time": event_time}],
                source="local",
            )

        if due_date is not None or self._looks_like_task(text):
            content = self._clean_content(text)
            return ParsedLog(
                notes=[],
                tasks=[
                    {
                        "content": content,
                        "due_date": due_date,
                    }
                ],
                events=[],
                source="local",
            )

        return ParsedLog(notes=[{"content": text}], tasks=[], events=[], source="local")

    def _extract_due_date(self, text: str) -> str | None:
        base = datetime.now().replace(second=0, microsecond=0)
        lowered = text.lower()
        target_date: datetime | None = None
        default_time: tuple[int, int] | None = None

        if "tomorrow" in lowered:
            target_date = base + timedelta(days=1)
        elif "today" in lowered:
            target_date = base
        elif "tonight" in lowered or "this evening" in lowered:
            target_date = base
            default_time = (19, 0)
        elif "this afternoon" in lowered:
            target_date = base
            default_time = (15, 0)
        elif "this morning" in lowered:
            target_date = base
            default_time = (9, 0)

        relative_match = re.search(r"\bin (\d+) (day|days|week|weeks)\b", lowered)
        if relative_match:
            quantity = int(relative_match.group(1))
            unit = relative_match.group(2)
            delta_days = quantity * 7 if "week" in unit else quantity
            target_date = base + timedelta(days=delta_days)

        weekday_match = re.search(
            r"\b(?:(next)\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
            lowered,
        )
        if weekday_match:
            is_next = weekday_match.group(1) is not None
            weekday_name = weekday_match.group(2)
            target_date = self._next_weekday(base, self.WEEKDAY_INDEX[weekday_name], force_next=is_next)

        parsed_time = self._extract_time_components(lowered)
        if target_date is None and parsed_time is None:
            return None

        if target_date is None:
            target_date = base

        if parsed_time is None and default_time is not None:
            hour, minute = default_time
        elif parsed_time is None:
            hour, minute = 9, 0
        else:
            hour, minute = parsed_time

        return target_date.replace(hour=hour, minute=minute).strftime(AI_DATETIME_FORMAT)

    def _extract_event_time(self, text: str) -> str | None:
        lowered = text.lower()
        if not self._looks_like_event(text):
            return None
        return self._extract_due_date(lowered)

    def _extract_time_components(self, text: str) -> tuple[int, int] | None:
        if "noon" in text:
            return 12, 0
        if "midnight" in text:
            return 0, 0
        match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", text)
        if not match:
            twenty_four_match = re.search(r"\b(?:at\s+)?([01]?\d|2[0-3]):([0-5]\d)\b", text)
            if not twenty_four_match:
                return None
            return int(twenty_four_match.group(1)), int(twenty_four_match.group(2))

        hour = int(match.group(1))
        minute = int(match.group(2) or "0")
        meridiem = match.group(3)

        if meridiem == "pm" and hour != 12:
            hour += 12
        if meridiem == "am" and hour == 12:
            hour = 0

        return hour, minute

    def _looks_like_task(self, text: str) -> bool:
        lowered = text.lower().strip()
        return lowered.startswith(self.TASK_PREFIXES) or any(
            phrase in lowered
            for phrase in (
                " today",
                " tomorrow",
                "tonight",
                "next monday",
                "next tuesday",
                "next wednesday",
                "next thursday",
                "next friday",
                "next saturday",
                "next sunday",
                " in ",
            )
        )

    def _looks_like_event(self, text: str) -> bool:
        lowered = text.lower()
        return any(marker in lowered for marker in self.EVENT_MARKERS)

    def _clean_content(self, text: str) -> str:
        cleaned = re.sub(
            r"\b(today|tomorrow|tonight|this morning|this afternoon|this evening)\b",
            "",
            text,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"\bin \d+ (day|days|week|weeks)\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(
            r"\bnext (monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(
            r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"\bat\s+\d{1,2}(?::\d{2})?\s*(am|pm)\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bat\s+(noon|midnight)\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bat\s+([01]?\d|2[0-3]):([0-5]\d)\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(
            r"^(remember to|need to|remind me to|don't forget to|todo:?|to do:?|task:?)\s+",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.-")
        return cleaned or text.strip()

    def _next_weekday(self, base: datetime, weekday: int, force_next: bool = False) -> datetime:
        days_ahead = (weekday - base.weekday()) % 7
        if force_next or days_ahead == 0:
            days_ahead = 7 if days_ahead == 0 else days_ahead + 7
        return base + timedelta(days=days_ahead)

    def validate_json(self, ai_json: str) -> ParsedLog:
        try:
            payload = json.loads(ai_json)
        except json.JSONDecodeError as exc:
            raise AIValidationError("AI response is not valid JSON.") from exc

        if not isinstance(payload, dict):
            raise AIValidationError("AI JSON payload must be an object.")

        expected_keys = {"notes", "tasks", "events"}
        if set(payload.keys()) != expected_keys:
            raise AIValidationError("AI JSON payload has unexpected top-level keys.")

        notes = self._validate_notes(payload["notes"])
        tasks = self._validate_tasks(payload["tasks"])
        events = self._validate_events(payload["events"])
        return ParsedLog(notes=notes, tasks=tasks, events=events, source="openai")

    def store_raw_log(self, raw_text: str, ai_json: str) -> int:
        with database_manager.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO raw_logs (raw_text, ai_json, created_at)
                VALUES (?, ?, ?)
                """,
                (raw_text, ai_json, serialize_datetime(datetime.now())),
            )
            return int(cursor.lastrowid)

    def persist_items(self, parsed_log: ParsedLog) -> None:
        for note in parsed_log.notes:
            notes_service.create_note(note["content"])
        for task in parsed_log.tasks:
            tasks_service.create_task(
                content=task["content"],
                due_date=parse_ai_datetime(task["due_date"]),
            )
        for event in parsed_log.events:
            event_time = parse_ai_datetime(event["event_time"])
            if event_time is None:
                raise AIValidationError("Event time cannot be null.")
            events_service.create_event(title=event["title"], event_time=event_time)

    def _validate_notes(self, notes: Any) -> list[dict[str, str]]:
        if not isinstance(notes, list):
            raise AIValidationError("'notes' must be an array.")
        validated: list[dict[str, str]] = []
        for item in notes:
            if not isinstance(item, dict) or set(item.keys()) != {"content"}:
                raise AIValidationError("Each note must contain only 'content'.")
            content = item.get("content")
            if not isinstance(content, str) or not content.strip():
                raise AIValidationError("Note content must be a non-empty string.")
            validated.append({"content": content.strip()})
        return validated

    def _validate_tasks(self, tasks: Any) -> list[dict[str, str | None]]:
        if not isinstance(tasks, list):
            raise AIValidationError("'tasks' must be an array.")
        validated: list[dict[str, str | None]] = []
        for item in tasks:
            if not isinstance(item, dict) or set(item.keys()) != {"content", "due_date"}:
                raise AIValidationError(
                    "Each task must contain exactly 'content' and 'due_date'."
                )
            content = item.get("content")
            due_date = item.get("due_date")
            if not isinstance(content, str) or not content.strip():
                raise AIValidationError("Task content must be a non-empty string.")
            if due_date is not None:
                if not isinstance(due_date, str):
                    raise AIValidationError("Task due_date must be a string or null.")
                parse_ai_datetime(due_date)
            validated.append({"content": content.strip(), "due_date": due_date})
        return validated

    def _validate_events(self, events: Any) -> list[dict[str, str]]:
        if not isinstance(events, list):
            raise AIValidationError("'events' must be an array.")
        validated: list[dict[str, str]] = []
        for item in events:
            if not isinstance(item, dict) or set(item.keys()) != {"title", "event_time"}:
                raise AIValidationError(
                    "Each event must contain exactly 'title' and 'event_time'."
                )
            title = item.get("title")
            event_time = item.get("event_time")
            if not isinstance(title, str) or not title.strip():
                raise AIValidationError("Event title must be a non-empty string.")
            if not isinstance(event_time, str):
                raise AIValidationError("Event event_time must be a string.")
            parse_ai_datetime(event_time)
            validated.append({"title": title.strip(), "event_time": event_time})
        return validated


ai_processor = AIProcessor()
