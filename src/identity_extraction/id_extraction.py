"""
ID/passport number extraction — pulling ID and passport numbers out of
extracted_data dicts produced by an OCR/extraction pipeline for Emirates ID,
passport, and similar identity documents.

Once a number is extracted, comparing it against another belongs in the
matching_utils package (matching_utils.id_matching) — see that package
for normalize_id_number/ids_match/find_conflicting_values.
"""

from __future__ import annotations

import re

from matching_utils.id_matching import normalize_id_number


def _nested_dict(fields: dict, key: str) -> dict:
    """Return fields[key] if it holds a dict, else an empty dict."""
    value = fields.get(key)
    return value if isinstance(value, dict) else {}


def extract_id_number(fields: dict) -> str | None:
    """
    Extract a normalized 15-digit Emirates ID number from an extracted_data dict.

    Tries the visible emirates_id / id_number field first (top-level and merged
    ID front sub-dict). Falls back to the last 15 digits of MRZ line 1 (TD1 format).
    """
    front = _nested_dict(fields, "front")
    raw = (
        fields.get("emirates_id")
        or fields.get("id_number")
        or front.get("emirates_id")
        or front.get("id_number")
    )
    if raw:
        normalized = normalize_id_number(str(raw))
        if normalized:
            return normalized
    back = _nested_dict(fields, "back")
    mrz = fields.get("machine_readable_zone") or back.get("machine_readable_zone")
    if mrz and isinstance(mrz, list) and mrz:
        digits = re.sub(r"\D", "", str(mrz[0]))
        if len(digits) >= 15:
            return digits[-15:]
    return None


def extract_passport_number(fields: dict) -> str | None:
    """
    Extract and normalize a passport number from an extracted_data dict.

    Tries the top level first, then the merged passport sub-dict (passport +
    passport_continue merge shape).
    """
    passport = _nested_dict(fields, "passport")
    raw = (
        fields.get("passport_number")
        or fields.get("passport_no")
        or fields.get("passport_num")
        or passport.get("passport_number")
        or passport.get("passport_no")
        or passport.get("passport_num")
    )
    if not raw:
        return None
    return re.sub(r"\s+", "", str(raw)).upper()
