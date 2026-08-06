"""
Name extraction — pulling person names out of extracted_data dicts produced
by an OCR/extraction pipeline for Emirates ID, passport, and similar identity
documents.

Once a name string is extracted, comparing it against another belongs in the
matching_utils package (matching_utils.name_matching) — see that
package for normalize_name/name_similarity/names_match/best_name_match.
"""

from __future__ import annotations

from dataclasses import dataclass

from matching_utils.name_matching import normalize_name


def _nested_dict(fields: dict, key: str) -> dict:
    """Return fields[key] if it holds a dict, else an empty dict."""
    value = fields.get(key)
    return value if isinstance(value, dict) else {}


@dataclass
class NamePair:
    """An english/arabic name found together at one level of an extracted_data dict."""

    english: str | None
    arabic: str | None
    role: str


def find_name_pairs(fields: dict) -> list[NamePair]:
    """
    Recursively search an extracted_data dict for every name field pair,
    at any nesting depth (nested objects and arrays of objects alike).

    Matches any key ending in "name_(english)" — the canonical schema style —
    or "name_english", the bare style raw extraction produces (seen when the
    formatting step falls back to raw data). Both may be role-prefixed (e.g.
    "owner_name_(english)", "broker_name_english"). Each match is paired with
    the same-style "…name_(arabic)" / "…name_arabic" key in the same object,
    if present. The role is the prefix (e.g. "owner"), or failing that the
    enclosing object's key (e.g. "tenant", "sellers") so callers can tell
    parties apart.
    """
    pairs: list[NamePair] = []
    _collect_name_pairs(fields, pairs, container_key="")
    return pairs


def _collect_name_pairs(node: object, pairs: list[NamePair], container_key: str) -> None:
    arabic_suffix_for = {"name_(english)": "name_(arabic)", "name_english": "name_arabic"}
    if isinstance(node, dict):
        for key in node:
            for english_suffix, arabic_suffix in arabic_suffix_for.items():
                if not key.endswith(english_suffix):
                    continue
                role_prefix = key[: -len(english_suffix)].rstrip("_")
                arabic_key = f"{role_prefix}_{arabic_suffix}" if role_prefix else arabic_suffix
                pairs.append(NamePair(
                    english=node.get(key),
                    arabic=node.get(arabic_key),
                    role=role_prefix or container_key,
                ))
                break
        for key, value in node.items():
            _collect_name_pairs(value, pairs, container_key=key)
    elif isinstance(node, list):
        for item in node:
            _collect_name_pairs(item, pairs, container_key=container_key)


def extract_all_names(fields: dict) -> list[str]:
    """
    Return every distinct normalized English name found anywhere in an
    extracted_data dict — top-level fields plus nested objects and arrays
    of party objects (sellers, buyers, tenant, landlord, heirs, etc.).
    """
    names: list[str] = []
    for pair in find_name_pairs(fields):
        if not pair.english:
            continue
        normalized = normalize_name(str(pair.english))
        if normalized and normalized not in names:
            names.append(normalized)
    return names


def extract_name(fields: dict) -> str | None:
    """
    Extract a normalized English name from an extracted_data dict.

    Searches every nesting level (top-level fields, nested objects such as
    front/passport/tenant/landlord, and arrays of party objects such as
    sellers/buyers) for a field ending in name_(english), returning the
    first match. Falls back to MRZ line 3 (SURNAME<<GIVEN_NAMES format,
    TD1/TD3) from the top-level, merged ID back sub-dict, or passport sub-dict.
    """
    for pair in find_name_pairs(fields):
        if pair.english:
            return normalize_name(str(pair.english))

    back = _nested_dict(fields, "back")
    passport = _nested_dict(fields, "passport")
    mrz = (
        fields.get("machine_readable_zone")
        or back.get("machine_readable_zone")
        or passport.get("machine_readable_zone")
    )
    if mrz and isinstance(mrz, list) and len(mrz) >= 3:
        raw = str(mrz[2]).replace("<", " ").strip()
        return normalize_name(raw) if raw else None
    return None
