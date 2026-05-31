"""Tests for knowledge/rxnav.py — RxNorm drug-name resolution.

Covers: exact match, approximate match (typos), failed lookup, thin-input
report, empty input, ingredient RxCUI, and edge cases around the HTTP layer.
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from backend.app.knowledge.rxnav import (
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

_METFORMIN_INGREDIENT = {
    "relatedGroup": {
        "rxcui": None,
        "conceptGroup": [
            {
                "tty": "IN",
                "conceptProperties": [{"rxcui": "6809", "name": "metformin", "tty": "IN"}],
            }
        ],
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

_LISINOPRIL_INGREDIENT = {
    "relatedGroup": {
        "rxcui": None,
        "conceptGroup": [
            {
                "tty": "IN",
                "conceptProperties": [{"rxcui": "197884", "name": "lisinopril", "tty": "IN"}],
            }
        ],
    }
}

_EMPTY_PROPS_RESPONSE = {"propConceptGroup": {"propConcept": []}}


def _mock_json_response(data: dict, status: int = 200) -> MagicMock:
    m = MagicMock()
    m.status_code = status
    m.json.return_value = data
    return m


@pytest.fixture(autouse=True)
def _reset_rxnav_client() -> None:
    """Reset the shared httpx client between tests."""
    import backend.app.knowledge.rxnav as rxnav_mod

    rxnav_mod._client_instance = None


# ── resolve_drug ───────────────────────────────────────────────────────────


class TestResolveDrug:
    def test_metformin_exact_match(self) -> None:
        """Known drug resolves with exact quality, ATC code, ingredient, and name."""
        responses = [
            _mock_json_response({"idGroup": {"rxnormId": ["6809"]}}),
            _mock_json_response(_METFORMIN_PROPS),
            _mock_json_response(_METFORMIN_INGREDIENT),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("metformin")

        assert result.resolved is True
        assert result.rxcui == "6809"
        assert result.ingredient_rxcui == "6809"
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
                            {
                                "rxcui": "6809",
                                "name": "metformin",
                                "score": "8.3",
                                "rank": "1",
                                "source": "RXNORM",
                            }
                        ]
                    }
                }
            ),
            _mock_json_response(_METFORMIN_PROPS),
            _mock_json_response(_METFORMIN_INGREDIENT),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("metformim")

        assert result.resolved is True
        assert result.rxcui == "6809"
        assert result.match_quality == "approximate"
        assert result.ingredient_rxcui == "6809"

    def test_unknown_drug_fails(self) -> None:
        """A completely unknown drug returns resolved=False."""
        responses = [
            _mock_json_response({"idGroup": {}}),  # exact fails
            _mock_json_response({"approximateGroup": {"candidate": []}}),  # approximate fails
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("zzzzzzzzz")

        assert result.resolved is False
        assert result.match_quality == "failed"
        assert result.rxcui is None
        assert result.ingredient_rxcui is None
        assert result.atc_codes == []

    def test_empty_string_fails_immediately(self) -> None:
        """Empty string returns failed without any API call."""
        result = resolve_drug("")
        assert result.resolved is False
        assert result.match_quality == "failed"

    def test_http_error_on_lookup_falls_to_approximate(self) -> None:
        """A 500 on exact lookup should still try approximate."""
        mock_500 = MagicMock()
        mock_500.status_code = 500
        mock_500.json.return_value = {}

        responses = [
            mock_500,
            _mock_json_response(
                {"approximateGroup": {"candidate": [{"rxcui": "6809", "name": "metformin"}]}}
            ),
            _mock_json_response(_METFORMIN_PROPS),
            _mock_json_response(_METFORMIN_INGREDIENT),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("metformin")

        assert result.resolved is True
        assert result.match_quality == "approximate"

    def test_http_error_on_properties_returns_minimal_result(self) -> None:
        """If the properties endpoint fails, return what we have."""
        responses = [
            _mock_json_response({"idGroup": {"rxnormId": ["6809"]}}),
            _mock_json_response({}, status=500),  # props fail
            _mock_json_response(_METFORMIN_INGREDIENT),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("metformin")

        assert result.resolved is True
        assert result.rxcui == "6809"
        assert result.atc_codes == []
        assert result.name == "metformin"  # falls back to input name

    def test_http_error_on_ingredient_returns_minimal_result(self) -> None:
        """If the ingredient endpoint fails, return what we have."""
        responses = [
            _mock_json_response({"idGroup": {"rxnormId": ["6809"]}}),
            _mock_json_response(_METFORMIN_PROPS),
            _mock_json_response({}, status=500),  # ingredient fails
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("metformin")

        assert result.resolved is True
        assert result.rxcui == "6809"
        assert result.ingredient_rxcui is None

    def test_approximate_returns_candidate_without_rxcui(self) -> None:
        """If approximate candidate has no rxcui, treat as failed."""
        responses = [
            _mock_json_response({"idGroup": {}}),
            _mock_json_response({"approximateGroup": {"candidate": [{"score": "1.0"}]}}),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("unknown")

        assert result.resolved is False

    def test_happy_path_lisinopril(self) -> None:
        """Lisinopril resolves with exact match and ingredient."""
        responses = [
            _mock_json_response({"idGroup": {"rxnormId": ["197884"]}}),
            _mock_json_response(_LISINOPRIL_PROPS),
            _mock_json_response(_LISINOPRIL_INGREDIENT),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("lisinopril")

        assert result.resolved is True
        assert result.rxcui == "197884"
        assert result.ingredient_rxcui == "197884"
        assert result.match_quality == "exact"
        assert "C09AA03" in result.atc_codes

    def test_propconcept_null_does_not_crash(self) -> None:
        """When RxNav returns propConcept=null, return empty list."""
        responses = [
            _mock_json_response({"idGroup": {"rxnormId": ["6809"]}}),
            # propConcept is explicitly null
            _mock_json_response({"propConceptGroup": {"propConcept": None}}),
            _mock_json_response(_METFORMIN_INGREDIENT),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("metformin")

        assert result.resolved is True
        assert result.rxcui == "6809"
        assert result.atc_codes == []
        assert result.name == "metformin"  # falls back to input

    def test_non_dict_item_in_props_skipped(self) -> None:
        """Non-dict items in the propConcept array are safely skipped."""
        adapter = MagicMock()
        adapter.side_effect = [
            _mock_json_response({"idGroup": {"rxnormId": ["6809"]}}),  # lookup
            _mock_json_response(  # properties with non-dict items
                {
                    "propConceptGroup": {
                        "propConcept": [
                            None,
                            "just a string",
                            {
                                "propCategory": "NAMES",
                                "propName": "NAME",
                                "propValue": "metFORMIN",
                            },
                        ]
                    }
                }
            ),
            _mock_json_response(_METFORMIN_INGREDIENT),  # ingredient
        ]

        # We need to be smarter about the multi-call
        adapter = MagicMock()
        adapter.side_effect = [
            _mock_json_response({"idGroup": {"rxnormId": ["6809"]}}),  # lookup
            _mock_json_response(  # properties with non-dict items
                {
                    "propConceptGroup": {
                        "propConcept": [
                            None,
                            "just a string",
                            {
                                "propCategory": "NAMES",
                                "propName": "NAME",
                                "propValue": "metFORMIN",
                            },
                        ]
                    }
                }
            ),
            _mock_json_response(_METFORMIN_INGREDIENT),  # ingredient
        ]

        mock_client = MagicMock()
        mock_client.get = adapter
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("metformin")

        assert result.resolved is True
        assert result.rxcui == "6809"
        assert result.name == "metFORMIN"

    def test_exact_match_returns_empty_id_group(self) -> None:
        """RxNav returns empty idGroup (not null) for unknown drug."""
        responses = [
            _mock_json_response({"idGroup": {"rxnormId": []}}),
            _mock_json_response({"approximateGroup": {"candidate": []}}),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("unknown")

        assert result.resolved is False


# ── resolve_drugs ──────────────────────────────────────────────────────────


class TestResolveDrugs:
    def test_all_resolved_no_note(self) -> None:
        """When all drugs resolve, no low-confidence note."""
        responses = [
            _mock_json_response({"idGroup": {"rxnormId": ["6809"]}}),
            _mock_json_response(_METFORMIN_PROPS),
            _mock_json_response(_METFORMIN_INGREDIENT),
            _mock_json_response({"idGroup": {"rxnormId": ["197884"]}}),
            _mock_json_response(_LISINOPRIL_PROPS),
            _mock_json_response(_LISINOPRIL_INGREDIENT),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
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
            _mock_json_response(_METFORMIN_INGREDIENT),
            _mock_json_response({"idGroup": {}}),  # fail
            _mock_json_response({"approximateGroup": {"candidate": []}}),
            _mock_json_response({"idGroup": {}}),  # fail
            _mock_json_response({"approximateGroup": {"candidate": []}}),
            _mock_json_response({"idGroup": {}}),  # fail
            _mock_json_response({"approximateGroup": {"candidate": []}}),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
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
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("metformin")

        assert result.resolved is False
        assert result.match_quality == "failed"

    def test_timeout_on_exact_falls_to_approximate(self) -> None:
        """A timeout on the exact match should try approximate."""
        mock_get = MagicMock(
            side_effect=[
                httpx.TimeoutException("timeout"),
                _mock_json_response(
                    {"approximateGroup": {"candidate": [{"rxcui": "6809", "name": "metformin"}]}}
                ),
                _mock_json_response(_METFORMIN_PROPS),
                _mock_json_response(_METFORMIN_INGREDIENT),
            ]
        )
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("metformin")

        assert result.resolved is True
        assert result.rxcui == "6809"

    # ── Coverage edge cases for unvisited branches ─────────────────────────────

    def test_non_200_on_approximate(self) -> None:
        """A non-200 from the approximate endpoint returns None (line 123)."""
        responses = [
            _mock_json_response({"idGroup": {}}),  # exact fails
            _mock_json_response({}, status=500),  # approximate 500
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("test")

        assert result.resolved is False

    def test_request_error_on_properties(self) -> None:
        """A network error on the properties endpoint returns [] (lines 151-152)."""
        responses = [
            _mock_json_response({"idGroup": {"rxnormId": ["6809"]}}),  # exact ok
            httpx.ConnectError("timeout fetching properties"),  # props fail
            _mock_json_response(_METFORMIN_INGREDIENT),  # ingredient ok
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("metformin")

        assert result.resolved is True
        assert result.rxcui == "6809"
        assert result.atc_codes == []
        assert result.name == "metformin"

    def test_request_error_on_ingredient(self) -> None:
        """A network error on ingredient returns None (lines 169-171)."""
        responses = [
            _mock_json_response({"idGroup": {"rxnormId": ["6809"]}}),
            _mock_json_response(_METFORMIN_PROPS),
            httpx.ConnectError("timeout fetching ingredient"),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("metformin")

        assert result.resolved is True
        assert result.rxcui == "6809"
        assert result.ingredient_rxcui is None

    def test_close_client_noop(self) -> None:
        """close_client() handles None gracefully (lines 92-93)."""
        from backend.app.knowledge.rxnav import _client_instance, close_client

        assert _client_instance is None
        close_client()
        assert _client_instance is None

    def test_get_client_creates_and_caches(self) -> None:
        """_get_client() initialises on first call, caches on second (lines 81-83)."""
        import backend.app.knowledge.rxnav as rxnav_mod

        assert rxnav_mod._client_instance is None

        mock_client = MagicMock()
        with patch("backend.app.knowledge.rxnav.httpx.Client", return_value=mock_client):
            client = rxnav_mod._get_client()
            assert client is mock_client
            assert rxnav_mod._client_instance is mock_client
            # Second call uses the cached instance
            client2 = rxnav_mod._get_client()
            assert client2 is mock_client

        rxnav_mod.close_client()
        assert rxnav_mod._client_instance is None
        mock_client.close.assert_called_once()

    def test_no_matching_ingredient_group(self) -> None:
        """When no conceptGroup has tty=IN, ingredient_rxcui is None (line 165)."""
        responses = [
            _mock_json_response({"idGroup": {"rxnormId": ["6809"]}}),
            _mock_json_response(_METFORMIN_PROPS),
            _mock_json_response(
                {
                    "relatedGroup": {
                        "rxcui": None,
                        "conceptGroup": [
                            {
                                "tty": "BN",
                                "conceptProperties": [{"rxcui": "xxx"}],
                            }
                        ],
                    }
                }
            ),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("metformin")

        assert result.resolved is True
        assert result.rxcui == "6809"
        assert result.ingredient_rxcui is None
