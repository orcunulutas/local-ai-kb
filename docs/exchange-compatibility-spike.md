# Exchange Compatibility Spike

## Objective
The objective of this spike is to validate connectivity and data access from a Linux environment to an on-premises Exchange mailbox through EWS (Exchange Web Services), specifically targeting a configurable folder path (defaulting to a `KB` directory sitting as a sibling to `Notes` under the `Top of Information Store` folder).

## Scope
* Connecting to an on-premises Exchange server via EWS.
* Authenticating securely (NTLM and Basic) without hardcoded credentials.
* Discovering and accessing a configurable target folder underneath a configurable semantic root folder.
* Enumerating Note items and retrieving diagnostic properties (Subject, Body, Creation/Modification Dates, Item ID, ChangeKey, Item Class).
* Demonstrating stateful incremental synchronization capabilities via `SyncFolderItems`.
* Persisting the opaque sync state in an ignored local file to test subsequent incremental syncs.

## Non-Goals
* Implementing the production `ExchangeNotesAdapter`.
* Implementing LLM enrichment.
* Implementing QMD.
* Implementing SQLite state synchronization.
* Modifying architecture unless actual EWS behaviors challenge foundational assumptions.

## Prerequisites
* Python 3.11 or newer.
* A valid configured `config.yaml` file (derived from `config.example.yaml`).
* Credentials injected via environment variables or interactive prompt.
* EWS Endpoint accessible from the test environment (if performing live validation).

## Configuration
Example setup in `config.yaml` matching the overall system architecture:

```yaml
sources:
  exchange_notes:
    endpoint: https://exchange.example.invalid/EWS/Exchange.asmx
    server: exchange.example.invalid
    email: user@example.invalid
    username: user@example.invalid
    auth_type: NTLM # NTLM or Basic
    # ca_cert_path: /path/to/custom/ca.crt # Optional custom CA certificate path
    # Supply secrets through the future secret provider/environment, not here.
    password_env: AIKB_EXCHANGE_PASSWORD
    checkpoint_key: exchange-notes
    folder:
      root: tois
      path: KB
```

**Note:** `endpoint` (mapped to `service_endpoint`) and `server` are alternatives for connection configuration. If both are specified, `endpoint` will take precedence in the spike configuration for determining the connection path.

Do not commit credentials or local configuration to the repository.

## Running the Probe
The compatibility spike probe can be run locally using the `tools/exchange_spike.py` script.
First, set your password (or leave unset for an interactive prompt). The variable used for this is derived from `password_env` in the configuration (defaulting to `EXCHANGE_PASSWORD`):

```bash
export AIKB_EXCHANGE_PASSWORD="your_secure_password"
```

To list all items in the configured target folder:
```bash
python tools/exchange_spike.py list --config config.yaml
```

To perform a stateful incremental sync:
```bash
python tools/exchange_spike.py sync --config config.yaml
```

## Expected Output
### `list` mode
Connects to the server, finds the folder, and lists diagnostic information for items.
```text
Connecting to Exchange...
Locating tois/KB folder...
resolved_folder_path: /root/Top of Information Store/KB
folder_class: IPF.StickyNote
total_count: 3

Item
----
ID: AQMk...
ChangeKey: CQAA...
SearchKey: 7365617263686B65795F31
Subject: Meeting Notes
Class: IPM.StickyNote
Created: 2024-05-10T10:00:00+00:00
Modified: 2024-05-10T10:15:00+00:00
Body: ...
```

### `sync` mode
The first execution outputs `sync_state_present: no`, runs the sync, outputs the changes, and persists the sync state to `.sync_state.txt`.

A subsequent execution will reuse `.sync_state.txt`:
```text
Incremental Sync
----------------
sync_state_present: yes
sync_state_length: 256
sync_state_fingerprint: a1b2c3d4
Executing sync_items...
created: 1
updated: 0
deleted: 0
new_sync_state_present: yes
new_sync_state_length: 260
new_sync_state_fingerprint: f8e7d6c5

Changes:
- CREATE: ID=AQMk..., ChangeKey=CQAA...
```

## SyncFolderItems Limitations & Follow-up Fetch Strategy
`SyncFolderItems` primarily returns identity and versioning information (`id`, `changekey`) and sometimes basic metadata depending on the EWS query configuration. It often does *not* return the complete text or HTML body of a Note.
A two-step fetch strategy may be required for production:
1. Call `sync_items` to retrieve lists of created, updated, and deleted items with their IDs and ChangeKeys.
2. For creations and updates, perform a bulk `fetch()` using the collected IDs to obtain full item properties, particularly `body`.

## Behaviors and Assumptions
### Confirmed by Automated Tests
* We can encapsulate `exchangelib` without bleeding its types to external layers.
* NTLM and Basic authentication config parameters can be mapped successfully.
* The API structure of locating subfolders and accessing `folder.all()` maps cleanly to diagnostic dictionary properties.
* `sync_items` correctly handles incremental states, sorting them into `create`, `update`, and `delete` buckets using `ChangeKey`.

### Confirmed by Real Exchange Validation
* EWS connectivity and authentication succeeded.
* Distinguished `Notes` folder discovery succeeded.
* The validated custom target folder was discovered directly under `Top of Information Store` (`tois`) and sits as a sibling of `Notes`. The target folder class was `IPF.StickyNote`.
* The previous assumption that the target folder would be a child of `Notes` was disproved.
* The target custom folder is successfully discovered even when empty.
* Initial incremental synchronization with items produced `CREATE`.
* A subsequent sync with no changes produced zero changes, but **the opaque sync state mutated anyway**, meaning state equality cannot be used as an idempotency signal.
* Editing the Note in the target folder produced an `UPDATE`. During in-folder edits, `ItemId` remained stable, while `ChangeKey` and modified timestamps changed.
* Moving the Note out of the target folder produced a `DELETE`.
* Moving the Note back into the target folder produced a `CREATE`.
* Moving between folders **changed the EWS ItemId**. EWS `ItemId` is a physical locator, not a durable logical identity.
* `PidTagSearchKey` (`PR_SEARCH_KEY`) is readable and remained identical across folder moves. It is the current candidate for a stable logical identity pending any further validations. `ChangeKey` acts as a revision token. Note that synthetic `ChangeKey` values on `DELETE` events do not represent a document revision.
* Moving items in Outlook was visible immediately locally before refreshing an EWS query. Closing Outlook allowed the server-side move to materialize. **EWS server state is authoritative for ingestion**.

### Production Adaptor Implications
* The production `ExchangeNotesAdapter` will require a durable source-specific mapping from current/previous EWS `ItemId` locators to their true logical identity (`SearchKey`). This deletion mapping is not implemented in this Phase 0 spike and must be isolated from the generic domain contracts.

### Still Requiring Real On-Prem Exchange Validation
* The exact fields omitted by `SyncFolderItems` requiring a secondary `fetch()` still need systematic characterization depending on the final production ingestion shape requirements.

## Known Limitations
* This spike is currently unable to reach the private on-premises Exchange endpoint from the cloud development environment.
* CA Certificates injection sets a global environment variable `REQUESTS_CA_BUNDLE` which works for the spike but needs a scoped approach if parallel connections to different endpoints were introduced in production.
