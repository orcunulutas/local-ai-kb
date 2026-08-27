# Implementation plan

Each phase must preserve the dependency rules in `ARCHITECTURE.md` and add
tests at the boundary it introduces.

## Phase 0 — foundation (this scaffold)

- Establish packaging, documentation, configuration shape, and test layout.
- Define immutable domain models and extension protocols.
- Provide explicit internal registries for built-in factories.
- Reserve Exchange, application, renderer, enrichment, processor, and sink
  namespaces without implementing external behavior.

## Phase 1 — local vertical slice

- Add configuration loading and validation.
- Implement an in-memory or fixture source adapter.
- Implement a deterministic baseline processor and Markdown renderer.
- Implement a filesystem sink (not QMD) and orchestration with idempotency.
- Add integration tests proving the complete contract flow.

## Phase 2 — synchronization state

- Add durable checkpoints, item identity mapping, deletion handling, and
  atomic advancement after successful writes.
- Define observable result/error reporting and retry policy.

## Phase 3 — Exchange Notes source

- Add shared EWS client functionality under `sources/exchange/client.py`.
- Add authentication through configuration/secrets without logging secrets.
- Implement `sources/exchange/notes.py` solely as a `SourceAdapter`.
- Test against recorded, sanitized protocol fixtures and an opt-in live suite.

## Phase 4 — enrichment

- Add an Ollama-backed `EnrichmentProvider` behind the existing protocol.
- Define timeouts, model/version provenance, deterministic fallbacks, and
  explicit failure behavior. Keep all LLM calls outside source adapters.

## Phase 5 — QMD sink

- Implement QMD only under `sinks/` as a `KnowledgeSink`.
- Encapsulate command execution, escaping, timeouts, and error translation.
- Verify processors and source adapters remain independent of QMD.

## Phase 6 — operations and additional adapters

- Add systemd packaging and operational documentation.
- Add Exchange mail ingestion as a separate source adapter reusing the shared
  Exchange client.
- Add metrics/logging and recovery tooling.

## Explicitly deferred

Dynamic third-party plugin loading, web APIs, and UI require separate design
decisions and are not implied by the internal registry mechanism.

