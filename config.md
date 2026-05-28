# GitDeck configuration

| Key | Type | Description |
|-----|------|-------------|
| `repo_path` | string | **Absolute** path to your local CrowdAnki git repository.<br>Example: `/Users/you/Decks/japanese-deck` |
| `deck_name` | string | Exact deck name as it appears in Anki, including `::` separators for sub-decks.<br>Example: `Japanese::Core 2000` |

**Requirements**

* CrowdAnki must be installed (AnkiWeb id `1788670778`).
* Your SSH keys and git remote must already be configured — GitDeck shells out to
  the system `git` binary and does not manage authentication.
* Anki 2.1.50 or later (uses `aqt.operations.QueryOp`).
