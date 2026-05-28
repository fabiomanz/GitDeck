# GitDeck

An Anki add-on that syncs a deck with a [CrowdAnki](https://github.com/Apehaenger/CrowdAnki) git repository via two Tools menu items.

| Menu item | What it does |
|-----------|-------------|
| **Pull & Import** | Runs `git pull` in your local repo, then imports the deck into Anki via CrowdAnki's `AnkiJsonImporter` |
| **Export & Push** | Exports the configured deck as CrowdAnki JSON into the repo directory, then runs `git add -A && git commit && git push` |

All git and network calls run off the UI thread using `aqt.operations.QueryOp`. Any error — including merge conflicts — aborts cleanly and shows a dialog instead of trying to auto-resolve.

---

## Requirements

- Anki **2.1.50** or later
- [CrowdAnki](https://ankiweb.net/shared/info/1788670778) add-on installed
- A local clone of your CrowdAnki git repository with SSH remotes already configured (GitDeck shells out to the system `git` binary and does not manage authentication)

---

## Installation

### From AnkiWeb *(coming soon)*

Install via Tools → Add-ons → Get Add-ons.

### Manual install

1. Download or clone this repository.
2. Copy the `GitDeck/` folder into your Anki add-ons directory:
   - **macOS**: `~/Library/Application Support/Anki2/addons21/gitdeck`
   - **Windows**: `%APPDATA%\Anki2\addons21\gitdeck`
   - **Linux**: `~/.local/share/Anki2/addons21/gitdeck`
3. Restart Anki.

---

## Configuration

Go to **Tools → Add-ons**, select GitDeck, and click **Config**.

```json
{
    "repo_path": "/absolute/path/to/your/crowdanki-repo",
    "deck_name": "My Deck"
}
```

| Key | Description |
|-----|-------------|
| `repo_path` | Absolute path to the local CrowdAnki git repository |
| `deck_name` | Exact deck name as shown in Anki, including `::` for sub-decks (e.g. `Japanese::Core 2000`) |

---

## Usage

Once configured:

- **Tools → Pull & Import** — fetches the latest changes from the remote and imports the deck. If there is a merge conflict or any git error, you will see an error dialog and no import will occur.
- **Tools → Export & Push** — exports the current state of the deck into the repo directory and pushes it. If the deck has not changed since the last export, the commit step is skipped and you will see a "nothing committed" tooltip.

---

## Contributing & local testing

### Project layout

```
GitDeck/
├── __init__.py   # all add-on logic
├── config.json   # default config (both fields empty)
├── config.md     # shown in Anki's built-in config editor
└── manifest.json # add-on metadata
```

### Set up a development environment

1. **Clone the repo**

   ```bash
   git clone https://github.com/fabiomanz/GitDeck.git
   ```

2. **Symlink into Anki's add-ons directory** so changes take effect on the next Anki restart without copying files manually.

   ```bash
   # macOS
   ln -s "$(pwd)/GitDeck" ~/Library/Application\ Support/Anki2/addons21/gitdeck

   # Linux
   ln -s "$(pwd)/GitDeck" ~/.local/share/Anki2/addons21/gitdeck
   ```

3. **Install CrowdAnki** (required at runtime). Install it via Anki's add-on browser (id `1788670778`) or from [its GitHub repo](https://github.com/Apehaenger/CrowdAnki).

4. **Restart Anki.** You should see "Pull & Import" and "Export & Push" in the Tools menu.

### Testing checklist

Before submitting a PR, manually verify the following scenarios:

**Pull & Import**
- [ ] Happy path: remote has new cards → deck is updated after pull
- [ ] No-op pull (already up to date) → import still runs without error
- [ ] Git error (e.g. no network, bad remote URL) → error dialog shown, no import attempted
- [ ] Merge conflict in repo → error dialog shown with git's conflict message

**Export & Push**
- [ ] Happy path: deck has changes → files written, commit created, push succeeds
- [ ] No changes since last export → "nothing committed" tooltip, no empty commit
- [ ] Deck name not found in collection → error dialog before any git operation
- [ ] Push rejected by remote (e.g. non-fast-forward) → error dialog with git's message

**Config**
- [ ] Missing `repo_path` or `deck_name` → error dialog on menu click, before any git/Anki operation
- [ ] Sub-deck name with `::` → export and import both work correctly

### Viewing add-on errors

If Anki crashes or the add-on silently fails, check the debug console:

- **macOS / Linux**: run Anki from the terminal — Python tracebacks print to stdout.
- **Windows**: use **Help → Open debug console** (or start `anki.exe` from a terminal).

### Releasing a new version

1. Bump `human_version` in `manifest.json`.
2. Zip the contents of the `GitDeck/` directory (**not** the directory itself):
   ```bash
   cd GitDeck
   zip -r ../gitdeck.ankiaddon __init__.py config.json config.md manifest.json
   ```
3. Upload `gitdeck.ankiaddon` to AnkiWeb.

---

## License

MIT
