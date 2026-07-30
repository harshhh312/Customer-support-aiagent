"""
PII Redaction & Restoration using Microsoft Presidio.
Scans text for PII (emails, credit cards, SSNs, names, etc.),
replaces them with unique placeholders, and restores them later.
"""

from presidio_analyzer import AnalyzerEngine
from typing import Dict, Tuple

# Initialize the analyzer (loads NLP models on first use)
analyzer = AnalyzerEngine()

# Entities we want to detect and redact
# We skip LOCATION and DATE to keep the conversation natural, but you can add them if needed.
# Default Presidio covers: PERSON, EMAIL_ADDRESS, PHONE_NUMBER, CREDIT_CARD, SSN, etc.
REDACTED_ENTITIES = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "CREDIT_CARD",
    "SSN",
    "US_SSN",
    "IBAN_CODE",
    "CRYPTO",
    "IP_ADDRESS",
]


def redact_pii(text: str) -> Tuple[str, Dict[str, str]]:
    """
    Detects PII in the text and replaces it with unique placeholders.
    Returns:
      - redacted_text: The text with PII replaced by {PII_1}, {PII_2}, etc.
      - mapping: A dict mapping {placeholder: original_text}
    """
    if not text or not text.strip():
        return text, {}

    # Analyze the text for PII
    results = analyzer.analyze(text=text, language="en")

    # Filter to only the entities we care about
    filtered_results = [r for r in results if r.entity_type in REDACTED_ENTITIES]

    if not filtered_results:
        return text, {}

    # Sort by start index in reverse order to safely replace from the end
    filtered_results = sorted(filtered_results, key=lambda x: x.start, reverse=True)

    mapping = {}
    idx = 1
    redacted_text = text

    for res in filtered_results:
        original = text[res.start:res.end]
        placeholder = f"{{PII_{idx}}}"
        mapping[placeholder] = original
        redacted_text = (
            redacted_text[:res.start] + placeholder + redacted_text[res.end:]
        )
        idx += 1

    return redacted_text, mapping


def restore_pii(text: str, mapping: Dict[str, str]) -> str:
    """
    Replaces placeholders like {PII_1} with the original PII values.
    """
    if not mapping:
        return text

    restored_text = text
    for placeholder, original in mapping.items():
        restored_text = restored_text.replace(placeholder, original)
    return restored_text