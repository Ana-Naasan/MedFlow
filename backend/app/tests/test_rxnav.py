"""Tests for knowledge/rxnav.py — RxNorm drug-name resolution.

Covers: exact match, approximate match (typos), failed lookup, thin-input
report, empty input, ingredient RxCUI, network-error detection, client
lifecycle, and edge cases around the HTTP layer.
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from backend.app.knowledge.rxnav import (
    DrugResolution,
    DrugResolutionReport,
    close_client,
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


# ── Client lifecycle ───────────────────────────────────────────────────────


class TestClientLifecycle:
    def test_get_client_creates_and_caches(self) -> None:
        import backend.app.knowledge.rxnav as rxnav_mod

        assert rxnav_mod._client_instance is None

        mock_client = MagicMock()
        with patch("backend.app.knowledge.rxnav.httpx.Client", return_value=mock_client):
            c1 = rxnav_mod._get_client()
            assert c1 is mock_client
            assert rxnav_mod._client_instance is mock_client
            c2 = rxnav_mod._get_client()
            assert c2 is mock_client

        close_client()
        assert rxnav_mod._client_instance is None
        mock_client.close.assert_called_once()

    def test_close_client_noop_when_none(self) -> None:
        import backend.app.knowledge.rxnav as rxnav_mod

        assert rxnav_mod._client_instance is None
        close_client()
        assert rxnav_mod._client_instance is None


# ── resolve_drug ───────────────────────────────────────────────────────────


class TestResolveDrug:
    def test_metformin_exact_match(self) -> None:
        responses = [
            _mock_json_response({"idGroup": {"rxnormId": ["6809"]}}),
            _mock_json_response(_METFORMIN_PROPS),
            _mock_json_response(_METFORMIN_INGREDIENT),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("metformin")

        assert result.resolved is True
        assert result.rxcui == "6809"
        assert result.ingredient_rxcui == "6809"
        assert result.match_quality == "exact"
        assert result.atc_codes == ["A10BA02"]
        assert result.name == "metFORMIN"
        assert result.input_name == "metformin"
        assert result.network_error is False

    def test_typo_uses_approximate_match(self) -> None:
        responses = [
            _mock_json_response({"idGroup": {}}),
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

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("metformim")

        assert result.resolved is True
        assert result.rxcui == "6809"
        assert result.match_quality == "approximate"
        assert result.ingredient_rxcui == "6809"

    def test_unknown_drug_fails(self) -> None:
        responses = [
            _mock_json_response({"idGroup": {}}),
            _mock_json_response({"approximateGroup": {"candidate": []}}),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("zzzzzzzzz")

        assert result.resolved is False
        assert result.match_quality == "failed"
        assert result.rxcui is None
        assert result.ingredient_rxcui is None
        assert result.atc_codes == []
        assert result.network_error is False

    def test_empty_string_fails_immediately(self) -> None:
        result = resolve_drug("")
        assert result.resolved is False
        assert result.match_quality == "failed"

    def test_happy_path_lisinopril(self) -> None:
        responses = [
            _mock_json_response({"idGroup": {"rxnormId": ["197884"]}}),
            _mock_json_response(_LISINOPRIL_PROPS),
            _mock_json_response(_LISINOPRIL_INGREDIENT),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("lisinopril")

        assert result.resolved is True
        assert result.rxcui == "197884"
        assert result.ingredient_rxcui == "197884"
        assert result.match_quality == "exact"
        assert "C09AA03" in result.atc_codes

    def test_propconcept_null_does_not_crash(self) -> None:
        responses = [
            _mock_json_response({"idGroup": {"rxnormId": ["6809"]}}),
            _mock_json_response({"propConceptGroup": {"propConcept": None}}),
            _mock_json_response(_METFORMIN_INGREDIENT),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("metformin")

        assert result.resolved is True
        assert result.rxcui == "6809"
        assert result.atc_codes == []
        assert result.name == "metformin"

    def test_non_dict_item_in_props_skipped(self) -> None:
        adapter = MagicMock()
        adapter.side_effect = [
            _mock_json_response({"idGroup": {"rxnormId": ["6809"]}}),
            _mock_json_response(
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
            _mock_json_response(_METFORMIN_INGREDIENT),
        ]
        mock_client = MagicMock()
        mock_client.get = adapter

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("metformin")

        assert result.resolved is True
        assert result.rxcui == "6809"
        assert result.name == "metFORMIN"

    def test_exact_match_returns_empty_id_group(self) -> None:
        responses = [
            _mock_json_response({"idGroup": {"rxnormId": []}}),
            _mock_json_response({"approximateGroup": {"candidate": []}}),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("unknown")

        assert result.resolved is False

    def test_http_error_on_lookup_falls_to_approximate(self) -> None:
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

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("metformin")

        assert result.resolved is True
        assert result.match_quality == "approximate"

    def test_no_matching_ingredient_group(self) -> None:
        responses = [
            _mock_json_response({"idGroup": {"rxnormId": ["6809"]}}),
            _mock_json_response(_METFORMIN_PROPS),
            _mock_json_response(
                {
                    "relatedGroup": {
                        "rxcui": None,
                        "conceptGroup": [{"tty": "BN", "conceptProperties": [{"rxcui": "xxx"}]}],
                    }
                }
            ),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("metformin")

        assert result.resolved is True
        assert result.rxcui == "6809"
        assert result.ingredient_rxcui is None

    def test_display_name_falls_back_to_input(self) -> None:
        responses = [
            _mock_json_response({"idGroup": {"rxnormId": ["6809"]}}),
            _mock_json_response(
                {
                    "propConceptGroup": {
                        "propConcept": [
                            {"propCategory": "CODES", "propName": "RxCUI", "propValue": "6809"}
                        ]
                    }
                }
            ),
            _mock_json_response(_METFORMIN_INGREDIENT),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("metformin")

        assert result.resolved is True
        assert result.name == "metformin"

    def test_empty_atc_values_filtered(self) -> None:
        responses = [
            _mock_json_response({"idGroup": {"rxnormId": ["6809"]}}),
            _mock_json_response(
                {
                    "propConceptGroup": {
                        "propConcept": [
                            {"propCategory": "NAMES", "propName": "NAME", "propValue": "test"},
                            {"propCategory": "CODES", "propName": "ATC", "propValue": "A10BA02"},
                            {"propCategory": "CODES", "propName": "ATC", "propValue": ""},
                            {"propCategory": "CODES", "propName": "ATC", "propValue": "  "},
                        ]
                    }
                }
            ),
            _mock_json_response(_METFORMIN_INGREDIENT),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("metformin")

        assert result.atc_codes == ["A10BA02"]

    def test_display_name_prefers_name_propname(self) -> None:
        responses = [
            _mock_json_response({"idGroup": {"rxnormId": ["6809"]}}),
            _mock_json_response(
                {
                    "propConceptGroup": {
                        "propConcept": [
                            {"propCategory": "NAMES", "propName": "SY", "propValue": "synonym"},
                            {"propCategory": "NAMES", "propName": "NAME", "propValue": "metFORMIN"},
                        ]
                    }
                }
            ),
            _mock_json_response(_METFORMIN_INGREDIENT),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("metformin")

        assert result.name == "metFORMIN"


# ── Network error detection ────────────────────────────────────────────────


class TestNetworkErrors:
    def test_lookup_network_error_sets_flag(self) -> None:
        mock_get = MagicMock(side_effect=httpx.ConnectError("connection refused"))
        mock_client = MagicMock()
        mock_client.get = mock_get

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("metformin")

        assert result.resolved is False
        assert result.network_error is True

    def test_lookup_network_error_then_no_approximate(self) -> None:
        mock_get = MagicMock(
            side_effect=[
                httpx.ConnectError("conn refused"),
                _mock_json_response({"approximateGroup": {"candidate": []}}),
            ]
        )
        mock_client = MagicMock()
        mock_client.get = mock_get

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("metformin")

        assert result.resolved is False
        assert result.network_error is True  # approx had no result, but net_err still True

    def test_approximate_network_error_sets_flag(self) -> None:
        responses = [
            _mock_json_response({"idGroup": {}}),
            httpx.ConnectError("conn refused"),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("metformin")

        assert result.resolved is False
        assert result.network_error is True

    def test_properties_network_error_sets_flag(self) -> None:
        responses = [
            _mock_json_response({"idGroup": {"rxnormId": ["6809"]}}),
            httpx.ConnectError("conn refused"),
            _mock_json_response(_METFORMIN_INGREDIENT),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("metformin")

        assert result.resolved is True
        assert result.network_error is True
        assert result.atc_codes == []

    def test_ingredient_network_error_sets_flag(self) -> None:
        responses = [
            _mock_json_response({"idGroup": {"rxnormId": ["6809"]}}),
            _mock_json_response(_METFORMIN_PROPS),
            httpx.ConnectError("conn refused"),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("metformin")

        assert result.resolved is True
        assert result.network_error is True
        assert result.ingredient_rxcui is None

    def test_report_network_error_true_when_any_fails(self) -> None:
        """A single network error propagates to the report."""
        # metformin: _lookup_name fails, then _approximate_match also fails
        # lisinopril: _lookup_name + _fetch_properties + _fetch_ingredient succeed
        mock_get = MagicMock(
            side_effect=[
                httpx.ConnectError("conn refused"),  # metformin _lookup_name
                httpx.ConnectError("conn refused"),  # metformin _approximate_match
                _mock_json_response(
                    {"idGroup": {"rxnormId": ["197884"]}}
                ),  # lisinopril _lookup_name
                _mock_json_response(_LISINOPRIL_PROPS),  # lisinopril _fetch_properties
                _mock_json_response(_LISINOPRIL_INGREDIENT),  # lisinopril _fetch_ingredient
            ]
        )
        mock_client = MagicMock()
        mock_client.get = mock_get

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            report = resolve_drugs(["metformin", "lisinopril"])

        assert report.network_error is True
        assert report.resolved_count == 1

    def test_report_network_error_false_when_all_ok(self) -> None:
        responses = [
            _mock_json_response({"idGroup": {"rxnormId": ["6809"]}}),
            _mock_json_response(_METFORMIN_PROPS),
            _mock_json_response(_METFORMIN_INGREDIENT),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            report = resolve_drugs(["metformin"])

        assert report.network_error is False


# ── Non-200 status codes ───────────────────────────────────────────────────


class TestNon200Status:
    def test_non_200_on_exact_falls_to_approximate(self) -> None:
        responses = [
            _mock_json_response({}, status=500),
            _mock_json_response({"approximateGroup": {"candidate": [{"rxcui": "6809"}]}}),
            _mock_json_response(_METFORMIN_PROPS),
            _mock_json_response(_METFORMIN_INGREDIENT),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("metformin")

        assert result.resolved is True
        assert result.match_quality == "approximate"

    def test_non_200_on_approximate_gives_failed(self) -> None:
        responses = [
            _mock_json_response({"idGroup": {}}),
            _mock_json_response({}, status=500),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("test")

        assert result.resolved is False

    def test_non_200_on_properties_returns_empty_list(self) -> None:
        responses = [
            _mock_json_response({"idGroup": {"rxnormId": ["6809"]}}),
            _mock_json_response({}, status=500),
            _mock_json_response(_METFORMIN_INGREDIENT),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("metformin")

        assert result.resolved is True
        assert result.atc_codes == []

    def test_non_200_on_ingredient_returns_none(self) -> None:
        responses = [
            _mock_json_response({"idGroup": {"rxnormId": ["6809"]}}),
            _mock_json_response(_METFORMIN_PROPS),
            _mock_json_response({}, status=500),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            result = resolve_drug("metformin")

        assert result.resolved is True
        assert result.ingredient_rxcui is None


# ── resolve_drugs ──────────────────────────────────────────────────────────


class TestResolveDrugs:
    def test_all_resolved_no_note(self) -> None:
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

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            report = resolve_drugs(["metformin", "lisinopril"])

        assert report.total_count == 2
        assert report.resolved_count == 2
        assert report.failed_count == 0
        assert report.low_confidence_note is None

    def test_thin_input_triggers_note(self) -> None:
        responses = [
            _mock_json_response({"idGroup": {"rxnormId": ["6809"]}}),
            _mock_json_response(_METFORMIN_PROPS),
            _mock_json_response(_METFORMIN_INGREDIENT),
            _mock_json_response({"idGroup": {}}),
            _mock_json_response({"approximateGroup": {"candidate": []}}),
            _mock_json_response({"idGroup": {}}),
            _mock_json_response({"approximateGroup": {"candidate": []}}),
            _mock_json_response({"idGroup": {}}),
            _mock_json_response({"approximateGroup": {"candidate": []}}),
        ]
        mock_get = MagicMock(side_effect=responses)
        mock_client = MagicMock()
        mock_client.get = mock_get

        with patch("backend.app.knowledge.rxnav._get_client", return_value=mock_client):
            report = resolve_drugs(["metformin", "unknown1", "unknown2", "unknown3"])

        assert report.total_count == 4
        assert report.resolved_count == 1
        assert report.failed_count == 3
        assert report.low_confidence_note is not None
        assert "limited input" in report.low_confidence_note

    def test_empty_input_sets_note(self) -> None:
        report = resolve_drugs([])
        assert report.total_count == 0
        assert report.low_confidence_note is not None
        assert "limited input" in report.low_confidence_note

    def test_dataclass_properties(self) -> None:
        resolutions = [
            DrugResolution(input_name="a", resolved=True),
            DrugResolution(input_name="b", resolved=False),
            DrugResolution(input_name="c", resolved=True),
        ]
        report = DrugResolutionReport(resolutions=resolutions)
        assert report.total_count == 3
        assert report.resolved_count == 2
        assert report.failed_count == 1

    def test_exactly_at_threshold_no_note(self) -> None:
        resolutions = [
            DrugResolution(input_name="a", resolved=True),
            DrugResolution(input_name="b", resolved=True),
            DrugResolution(input_name="c", resolved=False),
            DrugResolution(input_name="d", resolved=False),
        ]
        report = DrugResolutionReport(resolutions=resolutions)
        assert report.low_confidence_note is None

    def test_below_threshold_triggers_note(self) -> None:
        resolutions = [
            DrugResolution(input_name="a", resolved=True),
            DrugResolution(input_name="b", resolved=True),
            DrugResolution(input_name="c", resolved=False),
            DrugResolution(input_name="d", resolved=False),
            DrugResolution(input_name="e", resolved=False),
        ]
        report = DrugResolutionReport(resolutions=resolutions)
        assert report.low_confidence_note is not None
