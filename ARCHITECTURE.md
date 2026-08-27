# Architecture

## Style and goals

The system is a modular monolith: one deployable Python application with
explicit in-process module boundaries. It favors understandable contracts,
local operation, incremental delivery, and replaceable adapters over a generic
plugin framework.

## Dependency direction

```text
                         application
             (composition and orchestration only)
              /        |        |        \
       sources     processors  renderers  sinks
           |          /   \        |       |
           +---------+ domain +-----+-------+
                         ^
                    enrichments
```

All extension modules may depend on `aikb.domain`. Domain code depends only on
the Python standard library. The application layer selects built-ins from
internal registries and wires them together. Lateral dependencies between
source, processor, renderer, and sink packages are forbidden.

### Non-negotiable boundaries

1. A `SourceAdapter` synchronizes one external source and emits source-neutral
   `SourceItem` values, represented in a `SyncResult` with `SourceChange`
   metadata. It knows nothing about processing, LLMs, rendering, or storage.
2. A `Processor` accepts a `SourceItem` and returns a `KnowledgeDocument`. It
   knows nothing about Exchange, EWS, QMD, or other infrastructure.
3. An `EnrichmentProvider` enriches source-neutral document data. Providers
   are injected into processing/orchestration; source adapters never call them.
4. A `Renderer` converts a `KnowledgeDocument` to a textual representation. It
   neither retrieves source data nor persists output.
5. A `KnowledgeSink` accepts `KnowledgeDocument` values for persistence or
   indexing. QMD, when implemented, is only a sink implementation. QMD types or
   commands must not leak into domain, processor, or source contracts.

## Domain contracts

- `SourceItem`: immutable, source-neutral content and provenance produced by a
  source adapter.
- `SourceChange`: an upsert or deletion observed during synchronization. An
  upsert carries a `SourceItem`; a deletion carries its stable external ID.
- `SyncResult`: immutable collection of changes plus the opaque checkpoint to
  use for the next synchronization.
- `KnowledgeDocument`: immutable canonical knowledge content produced by a
  processor, including traceability to its source item.

Protocols use synchronous methods at the domain boundary. Implementations may
perform asynchronous work internally or future application ports may introduce
async orchestration, but transport mechanics must not contaminate domain
values. Metadata is read-only and JSON-like by convention; integrations should
namespace source-specific keys.

## Package ownership

```text
src/aikb/
  domain/          models and protocols; no infrastructure imports
  application/     future use-case orchestration and composition
  sources/         source adapters
    exchange/      reusable Exchange infrastructure
      client.py    future shared EWS client boundary
      notes.py     future Notes adapter
      mail.py      future mail adapter (not currently created)
  processors/      SourceItem-to-KnowledgeDocument implementations
  enrichments/     optional enrichment providers
  renderers/       document renderers
  sinks/           persistence/indexing adapters; future QMD lives here
  registries/      explicit registries and built-in declarations
```

Reusable Exchange client, authentication, paging, retry, and EWS translation
code belongs in `sources/exchange/client.py` (and nearby Exchange-only support
modules). `notes.py` and future `mail.py` remain independent source adapters
that share this infrastructure. There is no Exchange code in processors.

## Composition and registries

Registries map explicit names to factories. Each capability has its own
registry, and built-in maps initially remain empty. Application composition
will populate/use those maps. Import-path discovery, entry points, arbitrary
module loading, and third-party plugin lifecycle are out of scope.

## Synchronization semantics

External identifiers must be stable within a source instance. Checkpoints are
opaque to application code and are advanced only from a successful
`SyncResult`. An upsert is idempotent by `(source, external_id)`; deletion is a
tombstone with the same identity. Partial failure policy, retries, and durable
checkpoint storage are deferred until orchestration is implemented.

## Testing strategy

Unit tests protect pure domain invariants, protocol conformance, and registries.
Integration tests will exercise module seams using fakes before real services
are enabled. External-service fixtures must be sanitized and deterministic;
live credentials and network dependence are prohibited in the default suite.

