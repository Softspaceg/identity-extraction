"""Tests for identity_extraction.id_extraction — ID/passport number extraction."""

from __future__ import annotations

from identity_extraction.id_extraction import extract_id_number, extract_passport_number


class TestExtractIdNumber:
    def test_top_level_emirates_id(self):
        assert extract_id_number({"emirates_id": "784-1111-1111111-1"}) == "784111111111111"

    def test_top_level_id_number_field(self):
        assert extract_id_number({"id_number": "784111111111111"}) == "784111111111111"

    def test_nested_under_merged_front(self):
        fields = {"front": {"emirates_id": "784-1111-1111111-1"}, "back": {}}
        assert extract_id_number(fields) == "784111111111111"

    def test_mrz_fallback_from_top_level(self):
        fields = {"machine_readable_zone": ["IDARE784111111111111<<<<<<<<<<<<<"]}
        assert extract_id_number(fields) == "784111111111111"

    def test_mrz_fallback_from_merged_back(self):
        fields = {"back": {"machine_readable_zone": ["IDARE784111111111111<<<<<<<<<<<<<"]}}
        assert extract_id_number(fields) == "784111111111111"

    def test_malformed_id_number_is_rejected_not_returned_raw(self):
        """A non-15-digit value should not be returned raw -- garbage in, None out."""
        assert extract_id_number({"emirates_id": "12345"}) is None

    def test_returns_none_when_nothing_found(self):
        assert extract_id_number({"area": "100 sqm"}) is None


class TestExtractPassportNumber:
    def test_top_level_passport_number(self):
        assert extract_passport_number({"passport_number": " ab123456 "}) == "AB123456"

    def test_top_level_passport_no_alias(self):
        assert extract_passport_number({"passport_no": "ab123456"}) == "AB123456"

    def test_nested_under_merged_passport(self):
        """passport + passport_continue merge shape nests the primary page under 'passport'."""
        fields = {
            "passport": {"passport_number": "ab123456"},
            "passport_continue": {"visa_pages": []},
        }
        assert extract_passport_number(fields) == "AB123456"

    def test_top_level_takes_priority_over_nested(self):
        fields = {"passport_number": "top123", "passport": {"passport_number": "nested456"}}
        assert extract_passport_number(fields) == "TOP123"

    def test_returns_none_when_nothing_found(self):
        assert extract_passport_number({"area": "100 sqm"}) is None
