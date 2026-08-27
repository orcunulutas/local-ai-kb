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

Copy `config.example.yaml` to `config.yaml`. The Exchange source refers to a
named entry under `credentials`; it never contains the password. For the
default Linux keyring provider, store the password once (the command prompts
for it without putting it in shell history):

```bash
python -m keyring set local-ai-kb.exchange user@example.invalid
```

Ensure Ollama and QMD are installed locally, then run:

```bash
aikb sync
# or without installing the console script:
python -m aikb sync
```

The configuration file is resolved relative to its own directory. On Linux,
Python keyring uses the desktop Secret Service backend when available. For a
headless job or tests, configure a credential with `provider: environment` and
an environment-variable name explicitly; there is no implicit environment
fallback.

See [ARCHITECTURE.md](ARCHITECTURE.md) for dependency rules and
[PLAN.md](PLAN.md) for incremental delivery stages.
