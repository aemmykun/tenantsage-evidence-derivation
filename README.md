# TenantSage Evidence Derivation

Governed derivation boundary for TenantSage / GEHRA.

This repository consumes only validated `GovernedSourceVersion` objects and produces immutable governed derived evidence suitable for later S4 retrieval.

## Invariant

**No valid governed source version -> no derivation.**

Derivation may preserve or tighten governance. It must never manufacture missing authority or broaden governed scope/classification.

## Pipeline

```text
GovernedSourceVersion
        |
        v
contract verification
        |
        v
semantic rendering / chunking
        |
        v
governance lineage propagation
        |
        v
derived classification + scope calculation
        |
        v
immutable chunk-version identity
        |
        v
embedding generation
        |
        v
GovernedDerivedEvidence
        |
        v
S3 sealed EEB -> S4 governed retrieval
```

## Owns

- deterministic source-version validation;
- structured-to-semantic rendering;
- chunking;
- governance lineage propagation;
- deterministic classification join / non-broadening scope rules;
- immutable logical chunk and chunk-version identifiers;
- content/governance hashes;
- embedding generation adapters;
- governed evidence persistence adapters;
- derivation proof events.

## Does not own

- authentication or IAM;
- S1 authority resolution;
- S2 requester governance decisions;
- S3 EEB compilation/sealing;
- requester access checks;
- S4 query authorization;
- LLM generation;
- mutable overwrite of an existing evidence version.

## Identity model

```text
logical_chunk_id
  = stable identity of a semantic boundary

chunk_version_id
  = immutable identity of one exact derived version
  = hash(source_version_id + logical_chunk_id + content_hash + governance_state_hash)
```

A changed source or governance state creates a new `chunk_version_id`; it does not overwrite the prior evidence version.

## Repository boundary

```text
tenantsage_ingestion
    -> GovernedSourceVersion
    -> tenantsage-evidence-derivation
    -> GovernedDerivedEvidence
    -> S3/S4 runtime
```

See `contracts/governed-derived-evidence.schema.json` and `src/tenantsage_evidence_derivation/core.py`.
