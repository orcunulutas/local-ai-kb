# local-ai-kb

`local-ai-kb` is a local-first knowledge ingestion system organized as a
modular monolith. This repository currently contains the architecture,
contracts, configuration example, and package skeleton only. It deliberately
does **not** connect to Exchange, Ollama, QMD, or any other external service.

The stable flow is:

```text
SourceAdapter -> SourceItem -> Processor -> KnowledgeDocument -> KnowledgeSink
                                      |              |
                              EnrichmentProvider   Renderer
```

The important boundaries are the two transformations
`SourceAdapter -> SourceItem` and
`SourceItem -> Processor -> KnowledgeDocument`. Source packages may translate
external data into source-neutral items, but cannot invoke processors,
renderers, enrichment providers, or sinks. Processors operate only on domain
objects and cannot know about Exchange or QMD. QMD belongs exclusively behind
the `KnowledgeSink` boundary.

## Repository status

Included now:

- immutable foundational domain models;
- structural Python protocols for extension points;
- simple internal registries for built-in implementations;
- namespace skeletons for sources, processors, enrichments, renderers, sinks,
  and application orchestration;
- unit tests for contract and registry behavior.

Deferred intentionally: Exchange/EWS connectivity and authentication, Notes
and mail synchronization, Ollama calls, QMD execution, systemd integration,
dynamic plugins, web APIs, and UI.

## Development

Python 3.11 or newer is required.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest
```

Copy `config.example.yaml` to a locally ignored configuration file when
implementation begins. Never commit credentials.

See [ARCHITECTURE.md](ARCHITECTURE.md) for dependency rules and
[PLAN.md](PLAN.md) for incremental delivery stages.

