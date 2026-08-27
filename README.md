# local-ai-kb

`local-ai-kb` is a local-first knowledge ingestion system organized as a
modular monolith. Its first usable pipeline incrementally synchronizes Exchange
Sticky Notes, enriches them with local Ollama, publishes deterministic
Markdown, and refreshes a QMD collection.

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

## MVP behavior

Included now:

- EWS `SyncFolderItems` incremental synchronization and full-item fetching;
- stable logical identity using `PidTagSearchKey`, including move-out and
  move-back handling when EWS changes the physical `ItemId`;
- durable SQLite checkpoints, locator mappings, and publication records;
- local Ollama JSON enrichment;
- atomic, deterministic Markdown publication under `published/`;
- QMD collection registration and incremental index refresh;
- offline integration coverage for add, edit, unpublish, and republish.

Mail ingestion, web UI, microservices, dynamic plugins, and Docker packaging
remain intentionally out of scope.

## Development

Python 3.11 or newer is required.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest
```

Copy `config.example.yaml` to `config.yaml`, set the configured Exchange
password environment variable, ensure Ollama and QMD are installed locally,
then run:

```bash
aikb sync
# or without installing the console script:
python -m aikb sync
```

The configuration file is resolved relative to its own directory. Never put
credentials in it; only the environment variable name is configured.

See [ARCHITECTURE.md](ARCHITECTURE.md) for dependency rules and
[PLAN.md](PLAN.md) for incremental delivery stages.
