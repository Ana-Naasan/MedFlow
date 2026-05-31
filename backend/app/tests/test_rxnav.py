"""Tests for knowledge/rxnav.py — RxNorm drug-name resolution.

Covers: exact match, approximate match (typos), failed lookup, thin-input
report, empty input, and edge cases around the HTTP layer.
"""

from unittest.mock import ANY, MagicMock, patch

import httpx
import pytest

from backend.app.knowledge.rxnav import (
    _THIN_INPUT_THRESHOLD,
    DrugResolution,
    DrugResolutionReport,
    resolve_drug,
    resolve_drugs,
)

# ── Fixtures ────────────────────────────────────────────────────────────────

_METFORMIN_PROPS = {
    "propConceptGroup": {
        "propConcept": [
            {"propCategory": "NAMES", "propName": "NAME", "propValue": "metFORMIN"},
            {"propCategory": "CODES", "propName": "ATC", "propValue": "A10BA02"},
            {"propCategory": "CODES", "propName": "RxCUI", "propValue": "6809"},
        ]
    }
}

_LISINOPRIL_PROPS = {
    "propConceptGroup": {
        "propConcept": [
            {"propCategory": "NAMES", "propName": "NAME", "propValue": "Lisinopril"},
            {"propCategory": "CODES", "propName": "ATC", "propValue": "C09AA03"},
            {"propCategory": "CODES", "propName": "RxCUI", "propValue": "197884"},
        ]
    }
}

_EMPTY_PROPS = {"propConceptGroup": {"propConcept": []}}


def _mock_json_response(data: dict, status: int = 200) -> MagicMock:
    m = MagicMock()
    m.status_code = status
    m.json.return_value = data
    m.raise_for_status = MagicMock()
    return m


# ── resolve_drug ───────────────────────────────────────────────────────────


class TestResolveDrug:
    def test_metformin_exact_match(self) -> None:
        """Known drug resolves with exact quality, ATC code, and name."""
        responses = [
            _mock_json_response({"idGroup": {"rxnormId": ["6809"]}}),
            _mock_json_response(_METFORMIN_PROPS),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_client.__enter__.return_value = mock_client

        with patch("backend.app.knowledge.rxnav._client", return_value=mock_client):
            result = resolve_drug("metformin")

        assert result.resolved is True
        assert result.rxcui == "6809"
        assert result.match_quality == "exact"
        assert result.atc_codes == ["A10BA02"]
        assert result.name == "metFORMIN"
        assert result.input_name == "metformin"

    def test_typo_uses_approximate_match(self) -> None:
        """A misspelled name should fall back to approximate match."""
        responses = [
            _mock_json_response({"idGroup": {}}),  # exact fails
            _mock_json_response(
                {
                    "approximateGroup": {
                        "candidate": [
                            {"rxcui": "6809", "name": "metformin", "score": "8.3", "rank": "1", "source": "RXNORM"}
                        ]
                    }
                }
            ),
            _mock_json_response(_METFORMIN_PROPS),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_client.__enter__.return_value = mock_client

        with patch("backend.app.knowledge.rxnav._client", return_value=mock_client):
            result = resolve_drug("metformim")

        assert result.resolved is True
        assert result.rxcui == "6809"
        assert result.match_quality == "approximate"
        assert result.atc_codes == ["A10BA02"]

    def test_unknown_drug_fails(self) -> None:
        """A completely unknown drug returns resolved=False."""
        responses = [
            _mock_json_response({"idGroup": {}}),  # exact fails
            _mock_json_response({"approximateGroup": {"candidate": []}}),  # approximate fails
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_client.__enter__.return_value = mock_client

        with patch("backend.app.knowledge.rxnav._client", return_value=mock_client):
            result = resolve_drug("zzzzzzzzz")

        assert result.resolved is False
        assert result.match_quality == "failed"
        assert result.rxcui is None
        assert result.atc_codes == []

    def test_http_error_on_lookup_falls_to_approximate(self) -> None:
        """A 500 on exact lookup should still try approximate."""
        mock_500 = MagicMock()
        mock_500.status_code = 500
        mock_500.json.return_value = {}

        responses = [
            mock_500,
            _mock_json_response(
                {
                    "approximateGroup": {
                        "candidate": [{"rxcui": "6809", "name": "metformin"}]
                    }
                }
            ),
            _mock_json_response(_METFORMIN_PROPS),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_client.__enter__.return_value = mock_client

        with patch("backend.app.knowledge.rxnav._client", return_value=mock_client):
            result = resolve_drug("metformin")

        assert result.resolved is True
        assert result.match_quality == "approximate"

    def test_http_error_on_properties_returns_minimal_result(self) -> None:
        """If the properties endpoint fails, return what we have."""
        responses = [
            _mock_json_response({"idGroup": {"rxnormId": ["6809"]}}),
            _mock_json_response({}, status=500),  # props fail
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_client.__enter__.return_value = mock_client

        with patch("backend.app.knowledge.rxnav._client", return_value=mock_client):
            result = resolve_drug("metformin")

        assert result.resolved is True
        assert result.rxcui == "6809"
        assert result.atc_codes == []
        assert result.name == "metformin"  # falls back to input name

    def test_approximate_returns_candidate_without_rxcui(self) -> None:
        """If approximate candidate has no rxcui, treat as failed."""
        responses = [
            _mock_json_response({"idGroup": {}}),
            _mock_json_response(
                {"approximateGroup": {"candidate": [{"score": "1.0"}]}}
            ),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_client.__enter__.return_value = mock_client

        with patch("backend.app.knowledge.rxnav._client", return_value=mock_client):
            result = resolve_drug("unknown")

        assert result.resolved is False

    def test_happy_path_lisinopril(self) -> None:
        """Lisinopril resolves with exact match."""
        responses = [
            _mock_json_response({"idGroup": {"rxnormId": ["197884"]}}),
            _mock_json_response(_LISINOPRIL_PROPS),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_client.__enter__.return_value = mock_client

        with patch("backend.app.knowledge.rxnav._client", return_value=mock_client):
            result = resolve_drug("lisinopril")

        assert result.resolved is True
        assert result.rxcui == "197884"
        assert result.match_quality == "exact"
        assert "C09AA03" in result.atc_codes


# ── resolve_drugs ──────────────────────────────────────────────────────────


class TestResolveDrugs:
    def test_all_resolved_no_note(self) -> None:
        """When all drugs resolve, no low-confidence note."""
        responses = [
            _mock_json_response({"idGroup": {"rxnormId": ["6809"]}}),
            _mock_json_response(_METFORMIN_PROPS),
            _mock_json_response({"idGroup": {"rxnormId": ["197884"]}}),
            _mock_json_response(_LISINOPRIL_PROPS),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_client.__enter__.return_value = mock_client

        with patch("backend.app.knowledge.rxnav._client", return_value=mock_client):
            report = resolve_drugs(["metformin", "lisinopril"])

        assert report.total_count == 2
        assert report.resolved_count == 2
        assert report.failed_count == 0
        assert report.low_confidence_note is None

    def test_thin_input_triggers_note(self) -> None:
        """When fewer than half resolve, the note is set."""
        responses = [
            _mock_json_response({"idGroup": {"rxnormId": ["6809"]}}),
            _mock_json_response(_METFORMIN_PROPS),
            _mock_json_response({"idGroup": {}}),  # fail
            _mock_json_response({"approximateGroup": {"candidate": []}}),  # fail
            _mock_json_response({"idGroup": {}}),  # fail
            _mock_json_response({"approximateGroup": {"candidate": []}}),  # fail
            _mock_json_response({"idGroup": {}}),  # fail
            _mock_json_response({"approximateGroup": {"candidate": []}}),  # fail
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_client.__enter__.return_value = mock_client

        with patch("backend.app.knowledge.rxnav._client", return_value=mock_client):
            report = resolve_drugs(["metformin", "unknown1", "unknown2", "unknown3"])

        assert report.total_count == 4
        assert report.resolved_count == 1
        assert report.failed_count == 3
        assert report.low_confidence_note is not None
        assert "limited input" in report.low_confidence_note

    def test_empty_input_sets_note(self) -> None:
        """Empty names list immediately gets the low-confidence note."""
        report = resolve_drugs([])
        assert report.total_count == 0
        assert report.low_confidence_note is not None
        assert "limited input" in report.low_confidence_note

    def test_dataclass_properties(self) -> None:
        """DrugResolutionReport computed properties work."""
        resolutions = [
            DrugResolution(input_name="a", resolved=True),
            DrugResolution(input_name="b", resolved=False),
            DrugResolution(input_name="c", resolved=True),
        ]
        report = DrugResolutionReport(resolutions=resolutions)
        assert report.total_count == 3
        assert report.resolved_count == 2
        assert report.failed_count == 1


# ── Thin-input threshold logic ─────────────────────────────────────────────


class TestThinInputThreshold:
    def test_exactly_at_threshold_no_note(self) -> None:
        """When exactly 50% resolve, no note (threshold is strictly less than)."""
        # 2 / 4 = 0.5 which is NOT less than 0.5
        resolutions = [
            DrugResolution(input_name="a", resolved=True),
            DrugResolution(input_name="b", resolved=True),
            DrugResolution(input_name="c", resolved=False),
            DrugResolution(input_name="d", resolved=False),
        ]
        report = DrugResolutionReport(resolutions=resolutions)
        assert report.low_confidence_note is None

    def test_below_threshold_triggers_note(self) -> None:
        """When 2/5 resolve (0.4 < 0.5), the note is set."""
        resolutions = [
            DrugResolution(input_name="a", resolved=True),
            DrugResolution(input_name="b", resolved=True),
            DrugResolution(input_name="c", resolved=False),
            DrugResolution(input_name="d", resolved=False),
            DrugResolution(input_name="e", resolved=False),
        ]
        report = DrugResolutionReport(resolutions=resolutions)
        assert report.low_confidence_note is not None


# ── Network error resilience ───────────────────────────────────────────────


class TestNetworkErrors:
    def test_connection_error_on_lookup_returns_failed(self) -> None:
        """A connection error should result in resolved=False."""
        mock_get = MagicMock(side_effect=httpx.ConnectError("connection refused"))
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_client.__enter__.return_value = mock_client

        with patch("backend.app.knowledge.rxnav._client", return_value=mock_client):
            result = resolve_drug("metformin")

        assert result.resolved is False
        assert result.match_quality == "failed"

    def test_timeout_on_exact_falls_to_approximate(self) -> None:
        """A timeout on the exact match should try approximate."""
        mock_get = MagicMock(
            side_effect=[
                httpx.TimeoutException("timeout"),
                _mock_json_response(
                    {
                        "approximateGroup": {
                            "candidate": [{"rxcui": "6809", "name": "metformin"}]
                        }
                    }
                ),
                _mock_json_response(_METFORMIN_PROPS),
            ]
        )
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_client.__enter__.return_value = mock_client

        with patch("backend.app.knowledge.rxnav._client", return_value=mock_client):
            result = resolve_drug("metformin")

        assert result.resolved is True
        assert result.rxcui == "6809"
