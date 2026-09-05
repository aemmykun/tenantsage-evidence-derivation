from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence


class DerivationError(ValueError):
    """Fail-closed derivation contract violation."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


REQUIRED_SOURCE_FIELDS = {
    "contract_version",
    "source_id",
    "source_version_id",
    "tenant_id",
    "scope_id",
    "data_classification",
    "status",
    "source_content_hash",
    "governance_state_hash",
    "provenance",
    "ingestion_decision",
    "proof_ref",
}


@dataclass(frozen=True)
class DerivedChunk:
    logical_chunk_id: str
    chunk_version_id: str
    source_id: str
    source_version_id: str
    tenant_id: str
    organisation_id: str | None
    scope_id: str
    data_classification: str
    visibility: str | None
    content: str
    content_hash: str
    governance_state_hash: str
    derivation_hash: str
    chunk_index: int
    parent_proof_ref: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "contract_version": "1.0",
            "logical_chunk_id": self.logical_chunk_id,
            "chunk_version_id": self.chunk_version_id,
            "source_id": self.source_id,
            "source_version_id": self.source_version_id,
            "tenant_id": self.tenant_id,
            "organisation_id": self.organisation_id,
            "scope_id": self.scope_id,
            "data_classification": self.data_classification,
            "visibility": self.visibility,
            "content": self.content,
            "content_hash": self.content_hash,
            "governance_state_hash": self.governance_state_hash,
            "derivation_hash": self.derivation_hash,
            "chunk_index": self.chunk_index,
            "parent_proof_ref": self.parent_proof_ref,
        }


def validate_governed_source_version(source: Mapping[str, Any]) -> None:
    missing = sorted(field for field in REQUIRED_SOURCE_FIELDS if not source.get(field))
    if missing:
        raise DerivationError(f"missing governed source fields: {', '.join(missing)}")

    if source.get("contract_version") != "1.0":
        raise DerivationError("unsupported governed source contract_version")

    if source.get("ingestion_decision") != "ALLOW":
        raise DerivationError("source is not admitted for derivation")

    if source.get("status") != "validated":
        raise DerivationError("source status is not validated")


def classification_join(
    classifications: Iterable[str],
    *,
    rank: Mapping[str, int],
) -> str:
    values = list(classifications)
    if not values:
        raise DerivationError("classification join requires at least one parent")

    unknown = [value for value in values if value not in rank]
    if unknown:
        raise DerivationError(f"unknown classifications: {', '.join(sorted(set(unknown)))}")

    return max(values, key=lambda value: rank[value])


def require_non_broadening_scope(parent_scopes: Sequence[str], derived_scope: str) -> str:
    """Conservative v1 rule: a derived chunk must remain inside every parent scope.

    Multi-parent scope intersection can replace this function when the canonical
    scope lattice is available. Until then, unequal parent scopes fail closed.
    """
    if not parent_scopes:
        raise DerivationError("at least one parent scope is required")

    unique = set(parent_scopes)
    if len(unique) != 1:
        raise DerivationError("parent scopes differ; canonical scope intersection is required")

    only_parent = next(iter(unique))
    if derived_scope != only_parent:
        raise DerivationError("derived scope would broaden or alter governed scope")

    return derived_scope


def build_chunk(
    source: Mapping[str, Any],
    *,
    content: str,
    chunk_index: int,
    semantic_boundary: str,
) -> DerivedChunk:
    validate_governed_source_version(source)

    normalized_content = content.strip()
    if not normalized_content:
        raise DerivationError("empty derived content")
    if chunk_index < 0:
        raise DerivationError("chunk_index must be >= 0")
    if not semantic_boundary.strip():
        raise DerivationError("semantic_boundary is required")

    logical_chunk_id = sha256_json(
        {
            "source_id": source["source_id"],
            "semantic_boundary": semantic_boundary,
        }
    )
    content_hash = sha256_text(normalized_content)

    derivation_descriptor = {
        "source_version_id": source["source_version_id"],
        "logical_chunk_id": logical_chunk_id,
        "chunk_index": chunk_index,
        "content_hash": content_hash,
        "governance_state_hash": source["governance_state_hash"],
    }
    derivation_hash = sha256_json(derivation_descriptor)
    chunk_version_id = derivation_hash

    return DerivedChunk(
        logical_chunk_id=logical_chunk_id,
        chunk_version_id=chunk_version_id,
        source_id=source["source_id"],
        source_version_id=source["source_version_id"],
        tenant_id=source["tenant_id"],
        organisation_id=source.get("organisation_id"),
        scope_id=source["scope_id"],
        data_classification=source["data_classification"],
        visibility=source.get("visibility"),
        content=normalized_content,
        content_hash=content_hash,
        governance_state_hash=source["governance_state_hash"],
        derivation_hash=derivation_hash,
        chunk_index=chunk_index,
        parent_proof_ref=source["proof_ref"],
    )
