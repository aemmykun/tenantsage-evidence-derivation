import pytest

from tenantsage_evidence_derivation.core import (
    DerivationError,
    build_chunk,
    classification_join,
    require_non_broadening_scope,
)


@pytest.fixture
def source():
    return {
        "contract_version": "1.0",
        "source_id": "SRC-001",
        "source_version_id": "SRCV-001",
        "tenant_id": "TENANT-001",
        "organisation_id": "ORG-001",
        "scope_id": "PROPERTY-001",
        "data_classification": "restricted",
        "visibility": "internal",
        "status": "validated",
        "source_content_hash": "a" * 64,
        "governance_state_hash": "b" * 64,
        "provenance": {"source_system": "test"},
        "ingestion_decision": "ALLOW",
        "proof_ref": "ledger:ingestion:001",
    }


def test_same_input_produces_same_chunk_version(source):
    a = build_chunk(source, content="Rack A contains switch 1.", chunk_index=0, semantic_boundary="row:1")
    b = build_chunk(source, content="Rack A contains switch 1.", chunk_index=0, semantic_boundary="row:1")
    assert a.chunk_version_id == b.chunk_version_id
    assert a.logical_chunk_id == b.logical_chunk_id


def test_content_mutation_creates_new_version(source):
    a = build_chunk(source, content="Rack A contains switch 1.", chunk_index=0, semantic_boundary="row:1")
    b = build_chunk(source, content="Rack A contains switch 2.", chunk_index=0, semantic_boundary="row:1")
    assert a.logical_chunk_id == b.logical_chunk_id
    assert a.chunk_version_id != b.chunk_version_id


def test_governance_mutation_creates_new_version(source):
    a = build_chunk(source, content="Rack A contains switch 1.", chunk_index=0, semantic_boundary="row:1")
    changed = dict(source)
    changed["governance_state_hash"] = "c" * 64
    b = build_chunk(changed, content="Rack A contains switch 1.", chunk_index=0, semantic_boundary="row:1")
    assert a.chunk_version_id != b.chunk_version_id


def test_denied_source_fails_closed(source):
    denied = dict(source)
    denied["ingestion_decision"] = "DENY"
    denied["status"] = "rejected"
    with pytest.raises(DerivationError):
        build_chunk(denied, content="data", chunk_index=0, semantic_boundary="row:1")


def test_classification_join_chooses_most_restrictive():
    rank = {"public": 0, "internal": 1, "restricted": 2, "confidential": 3}
    assert classification_join(["internal", "confidential"], rank=rank) == "confidential"


def test_scope_cannot_broaden():
    assert require_non_broadening_scope(["PROPERTY-001"], "PROPERTY-001") == "PROPERTY-001"
    with pytest.raises(DerivationError):
        require_non_broadening_scope(["PROPERTY-001"], "TENANT-WIDE")
