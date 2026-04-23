"""Contract tests for graph-freshness OpenAPI document."""
from __future__ import annotations

from pathlib import Path

import yaml


def _load_contract() -> dict:
    contract_path = (
        Path(__file__).resolve().parents[2]
        / "specs"
        / "019-understand-anything-swap"
        / "contracts"
        / "graph-freshness.openapi.yaml"
    )
    return yaml.safe_load(contract_path.read_text(encoding="utf-8"))


def test_graph_freshness_operations_exist() -> None:
    contract = _load_contract()
    paths = contract["paths"]

    assert "/graph/bootstrap/verify" in paths
    assert "/graph/impact/evaluate" in paths
    assert "/graph/freshness/validate" in paths


def test_operation_ids_match_spec_expectations() -> None:
    contract = _load_contract()

    assert contract["paths"]["/graph/bootstrap/verify"]["post"]["operationId"] == "verifyGraphBootstrap"
    assert contract["paths"]["/graph/impact/evaluate"]["post"]["operationId"] == "evaluateGraphImpact"
    assert contract["paths"]["/graph/freshness/validate"]["post"]["operationId"] == "validateGraphFreshness"


def test_freshness_response_enums_are_defined() -> None:
    contract = _load_contract()
    schemas = contract["components"]["schemas"]

    freshness_status = schemas["FreshnessValidationResponse"]["properties"]["status"]["enum"]
    freshness_state = schemas["FreshnessValidationResponse"]["properties"]["freshnessState"]["enum"]

    assert freshness_status == ["pass", "fail", "indeterminate"]
    assert freshness_state == ["CURRENT", "STALE", "MISSING", "INDETERMINATE"]


def test_required_check_name_is_modeled_in_freshness_contract() -> None:
    contract = _load_contract()
    schemas = contract["components"]["schemas"]

    request_props = schemas["FreshnessValidationRequest"]["properties"]
    response_props = schemas["FreshnessValidationResponse"]["properties"]

    assert request_props["requiredCheckName"]["default"] == "dev-stack-graph-freshness"
    assert response_props["requiredCheckName"]["default"] == "dev-stack-graph-freshness"
