# Exchange Compatibility Spike

## Objective
The objective of this spike is to validate connectivity and data access from a Linux environment to an on-premises Exchange mailbox through EWS (Exchange Web Services), specifically targeting the `Notes/AI-KB` directory.

## Scope
* Connecting to an on-premises Exchange server via EWS.
* Authenticating securely (NTLM and Basic) without hardcoded credentials.
* Discovering and accessing the `Notes/AI-KB` folder.
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
```

**Note:** `endpoint` (mapped to `service_endpoint`) and `server` are alternatives for connection configuration. If both are specified, `endpoint` will take precedence in the spike configuration for determining the connection path.

Do not commit credentials or local configuration to the repository.

## Running the Probe
The compatibility spike probe can be run locally using the `tools/exchange_spike.py` script.
First, set your password (or leave unset for an interactive prompt). The variable used for this is derived from `password_env` in the configuration (defaulting to `EXCHANGE_PASSWORD`):

```bash
export AIKB_EXCHANGE_PASSWORD="your_secure_password"
```

To list all items in the `Notes/AI-KB` folder:
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
Locating Notes/AI-KB folder...
Found AI-KB folder. Enumerating items...

Total items found: 3

Item
----
ID: AQMk...
ChangeKey: CQAA...
Subject: Meeting Notes
Class: IPM.Note
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
A two-step fetch strategy is required for production:
1. Call `sync_items` to retrieve lists of created, updated, and deleted items with their IDs and ChangeKeys.
2. For creations and updates, perform a bulk `fetch()` using the collected IDs to obtain full item properties, particularly `body`.

## Behaviors and Assumptions
### Confirmed by Automated Tests
* We can encapsulate `exchangelib` without bleeding its types to external layers.
* NTLM and Basic authentication config parameters can be mapped successfully.
* The API structure of locating subfolders and accessing `folder.all()` maps cleanly to diagnostic dictionary properties.
* `sync_items` correctly handles incremental states, sorting them into `create`, `update`, and `delete` buckets using `ChangeKey`.

### Still Requiring Real On-Prem Exchange Validation
The following behavior has been designed around but requires validation against a real server:
* Reliability of locating the `Notes` folder and its `AI-KB` child folder explicitly via EWS on this particular Exchange version.
* Stability of `ItemId` values across edits.
* Verification that `SyncFolderItems` accurately reports changes when items are:
  - Edited in Outlook.
  - Deleted from the `AI-KB` folder.
  - Moved out of the `AI-KB` folder.
  - Moved back into the `AI-KB` folder.
* Verification of `ChangeKey` mutation semantics on standard field updates.
* Exact fields omitted by `SyncFolderItems` requiring a secondary `fetch()`.

## Known Limitations
* This spike is currently unable to reach the private on-premises Exchange endpoint from the cloud development environment.
* CA Certificates injection sets a global environment variable `REQUESTS_CA_BUNDLE` which works for the spike but needs a scoped approach if parallel connections to different endpoints were introduced in production.
