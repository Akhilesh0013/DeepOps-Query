from __future__ import annotations

import logging
import re
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

_PII_PATTERNS: list[tuple[str, str]] = [
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[REDACTED_EMAIL]"),
    (r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "[REDACTED_PHONE]"),
    (r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "[REDACTED_CARD]"),
    (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[REDACTED_IP]"),
]

# Structured PII only — excludes PERSON, which NER mis-detects in technical terms
# (e.g. "kubernetes" → "<PERSON>uber<PERSON>es").
_STRUCTURED_PII_ENTITY_TYPES = [
    "CREDIT_CARD",
    "CRYPTO",
    "EMAIL_ADDRESS",
    "IBAN_CODE",
    "IP_ADDRESS",
    "PHONE_NUMBER",
    "US_SSN",
    "US_BANK_NUMBER",
    "CREDIT_CARD_RE",
    "UUID",
    "EMAIL_ADDRESS_RE",
    "US_SSN_RE",
]


def _load_moderation() -> Any | None:
    try:
        from llm_guard import scan_output
        return scan_output
    except Exception:
        logger.debug("llm-guard output scan not available; using fallback")
        return None

_SCAN_OUTPUT = _load_moderation()
_pii_scanners: list[Any] | None = None
_moderation_scanners: list[Any] | None = None


def _regex_redact_pii(text: str) -> str:
    for pattern, replacement in _PII_PATTERNS:
        text = re.sub(pattern, replacement, text)
    return text


def _get_pii_scanners() -> list[Any]:
    """Lazy-build llm-guard Sensitive scanner for structured PII (no PERSON)."""
    global _pii_scanners
    if _pii_scanners is not None:
        return _pii_scanners
    from llm_guard.output_scanners import Sensitive

    _pii_scanners = [
        Sensitive(
            redact=True,
            threshold=settings.output_toxicity_threshold,
            entity_types=_STRUCTURED_PII_ENTITY_TYPES,
        )
    ]
    return _pii_scanners


def _get_moderation_scanners() -> list[Any]:
    global _moderation_scanners
    if _moderation_scanners is not None:
        return _moderation_scanners
    from llm_guard.output_scanners import BanTopics, Toxicity

    _moderation_scanners = [
        Toxicity(threshold=settings.output_toxicity_threshold),
        BanTopics(
            topics=["violence", "self-harm", "illegal activities"],
            threshold=0.9,
        ),
    ]
    return _moderation_scanners


def redact_pii(text: str) -> str:
    if _SCAN_OUTPUT is not None:
        try:
            scanners = _get_pii_scanners()
            sanitized, _, _ = _SCAN_OUTPUT(scanners, "", text)
            return str(sanitized)
        except Exception:
            logger.exception("llm-guard PII redaction failed; using regex fallback")

    return _regex_redact_pii(text)


def moderate_output(text: str) -> tuple[bool, str | None]:
    """Moderate LLM output text. Returns (allowed, reason_or_none)."""
    if _SCAN_OUTPUT is not None:
        try:
            scanners = _get_moderation_scanners()
            _, is_valid, _ = _SCAN_OUTPUT(scanners, "", text)
            failed = [name for name, valid in is_valid.items() if not valid]
            if failed:
                checks = ", ".join(failed)
                return False, f"Output blocked by {checks}"
            return True, None
        except Exception:
            logger.exception("llm-guard output moderation failed; allowing")

    return True, None


def moderate_input(text: str) -> tuple[bool, str, str | None]:
    """Moderate a user question without NER-based redaction.

    NER falsely tags substrings in technical terms (e.g. "kubernetes") as PERSON.
    Input uses regex-only PII patterns for emails, phones, etc.
    """
    allowed, reason = moderate_output(text)
    redacted = _regex_redact_pii(text)
    return allowed, redacted, reason


def moderate_and_redact(text: str) -> tuple[bool, str, str | None]:
    """Moderate LLM output and redact structured PII. Returns (allowed, redacted_text, reason)."""
    allowed, reason = moderate_output(text)
    redacted = redact_pii(text)
    return allowed, redacted, reason
