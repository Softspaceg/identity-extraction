"""
Tests for identity_extraction.name_extraction — name extraction from
extracted_data dicts.

Covers: find_name_pairs recursion (nested objects, arrays of party objects,
role-prefixed fields), extract_all_names, and extract_name backward
compatibility (flat fields, merged ID front/back, passport, MRZ fallback).
"""

from __future__ import annotations

from identity_extraction.name_extraction import extract_all_names, extract_name, find_name_pairs


class TestFindNamePairsFlat:
    def test_bare_name_fields_at_top_level(self):
        fields = {"name_(english)": "John Smith", "name_(arabic)": "جون سميث"}
        pairs = find_name_pairs(fields)
        assert len(pairs) == 1
        assert pairs[0].english == "John Smith"
        assert pairs[0].arabic == "جون سميث"
        assert pairs[0].role == ""

    def test_missing_arabic_sibling_leaves_it_none(self):
        fields = {"name_(english)": "John Smith"}
        pairs = find_name_pairs(fields)
        assert pairs[0].english == "John Smith"
        assert pairs[0].arabic is None

    def test_no_name_fields_returns_empty(self):
        assert find_name_pairs({"emirates_id": "784-1111-1111111-1"}) == []


class TestFindNamePairsRolePrefixed:
    def test_owner_prefixed_pair(self):
        fields = {
            "owner_name_(english)": "Jane Doe",
            "owner_name_(arabic)": "جين دو",
        }
        pairs = find_name_pairs(fields)
        assert len(pairs) == 1
        assert pairs[0].english == "Jane Doe"
        assert pairs[0].role == "owner"

    def test_multiple_prefixed_pairs_on_same_level(self):
        fields = {
            "payer_name_(english)": "Alice",
            "payer_name_(arabic)": "أليس",
            "payee_name_(english)": "Bob",
            "payee_name_(arabic)": "بوب",
        }
        pairs = {p.role: p.english for p in find_name_pairs(fields)}
        assert pairs == {"payer": "Alice", "payee": "Bob"}


class TestFindNamePairsNested:
    def test_name_nested_one_level_under_front(self):
        fields = {
            "front": {"name_(english)": "John Smith", "name_(arabic)": "جون سميث"},
            "back": {"card_number": "123"},
        }
        pairs = find_name_pairs(fields)
        assert len(pairs) == 1
        assert pairs[0].english == "John Smith"
        assert pairs[0].role == "front"

    def test_name_nested_inside_arbitrary_container_key(self):
        """A 'details' wrapper object should not hide the name field, regardless of key name."""
        fields = {"details": {"name_(english)": "Carlos Ruiz", "name_(arabic)": "كارلوس"}}
        pairs = find_name_pairs(fields)
        assert len(pairs) == 1
        assert pairs[0].english == "Carlos Ruiz"
        assert pairs[0].role == "details"

    def test_name_nested_multiple_levels_deep(self):
        fields = {"level1": {"level2": {"level3": {"name_(english)": "Deep Name"}}}}
        pairs = find_name_pairs(fields)
        assert len(pairs) == 1
        assert pairs[0].english == "Deep Name"

    def test_names_inside_array_of_party_objects(self):
        fields = {
            "sellers": [
                {"name_(english)": "Seller One", "name_(arabic)": "بائع"},
                {"name_(english)": "Seller Two", "name_(arabic)": "بائع2"},
            ],
            "buyers": [{"name_(english)": "Buyer One", "name_(arabic)": "مشتري"}],
        }
        pairs = find_name_pairs(fields)
        names_by_role = sorted((p.role, p.english) for p in pairs)
        assert names_by_role == [
            ("buyers", "Buyer One"),
            ("sellers", "Seller One"),
            ("sellers", "Seller Two"),
        ]

    def test_finds_all_parties_across_mixed_structures(self):
        fields = {
            "tenant": {"name_(english)": "Tenant Person"},
            "landlord": {"name_(english)": "Landlord Person"},
            "property_info": {"address": "Some street"},
        }
        english_names = {p.english for p in find_name_pairs(fields)}
        assert english_names == {"Tenant Person", "Landlord Person"}


class TestFindNamePairsBareStyle:
    """Raw extraction produces name_english/name_arabic (no parentheses);
    these reach validation when the formatting step falls back to raw data."""

    def test_bare_style_at_top_level(self):
        pairs = find_name_pairs({"name_english": "John Smith", "name_arabic": "جون سميث"})
        assert len(pairs) == 1
        assert pairs[0].english == "John Smith"
        assert pairs[0].arabic == "جون سميث"

    def test_bare_style_with_role_prefix(self):
        pairs = find_name_pairs({"broker_name_english": "Ricky Wolf", "broker_name_arabic": "ريكي ولف"})
        assert len(pairs) == 1
        assert pairs[0].role == "broker"
        assert pairs[0].arabic == "ريكي ولف"

    def test_bare_style_nested_in_form_f_structure(self):
        """Regression: the Form F owner_details shape that validation used to miss."""
        fields = {
            "owner_details": {
                "owner_1": {"name_english": "FARZANA ATHAR HUSAIN", "name_arabic": "فرزانه"},
                "owner_2": {"name_english": "ANAM ABBAS MASUD", "name_arabic": "انام"},
            },
        }
        english_names = {p.english for p in find_name_pairs(fields)}
        assert english_names == {"FARZANA ATHAR HUSAIN", "ANAM ABBAS MASUD"}

    def test_bare_and_canonical_styles_do_not_double_count(self):
        pairs = find_name_pairs({"name_(english)": "John Smith"})
        assert len(pairs) == 1


class TestExtractAllNames:
    def test_dedupes_and_normalizes(self):
        fields = {
            "name_(english)": "John Smith",
            "sellers": [{"name_(english)": "John Smith"}, {"name_(english)": "Jane Doe"}],
        }
        assert extract_all_names(fields) == ["john smith", "jane doe"]

    def test_skips_pairs_with_no_english_value(self):
        fields = {"owner_name_(arabic)": "مالك"}
        assert extract_all_names(fields) == []

    def test_empty_when_no_names_present(self):
        assert extract_all_names({"area": "100 sqm"}) == []


class TestExtractNameBackwardCompatibility:
    def test_flat_top_level(self):
        assert extract_name({"name_(english)": "John Smith"}) == "john smith"

    def test_merged_id_front_back(self):
        fields = {
            "front": {"name_(english)": "John Smith"},
            "back": {"card_number": "123"},
        }
        assert extract_name(fields) == "john smith"

    def test_passport_sub_dict(self):
        fields = {"passport": {"name_(english)": "Jane Doe"}}
        assert extract_name(fields) == "jane doe"

    def test_mrz_fallback_when_no_name_field(self):
        fields = {"machine_readable_zone": ["L1", "L2", "SMITH<<JOHN"]}
        assert extract_name(fields) == "smith john"

    def test_name_field_takes_priority_over_mrz(self):
        fields = {
            "name_(english)": "John Smith",
            "machine_readable_zone": ["L1", "L2", "OTHER<<PERSON"],
        }
        assert extract_name(fields) == "john smith"

    def test_returns_none_when_nothing_found(self):
        assert extract_name({"area": "100 sqm"}) is None

    def test_finds_name_buried_in_nested_details_field(self):
        """Regression: a 'details' wrapper (or any non-hardcoded container) must not hide the name."""
        fields = {"details": {"party": {"name_(english)": "Buried Name"}}}
        assert extract_name(fields) == "buried name"
