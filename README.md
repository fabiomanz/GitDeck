# GitDeck

An Anki add-on that keeps a deck in sync with a [CrowdAnki](https://github.com/Apehaenger/CrowdAnki) git repository. Two buttons in the toolbar (and matching items in the Tools menu) handle the full pull and push workflow.

| Action | What it does |
|--------|-------------|
| **Pull** | Runs `git pull`, imports the deck, and deletes any notes that were removed from the repo — so deletions propagate to everyone |
| **Push** | Exports the deck as CrowdAnki JSON and runs `git commit && git push` |

The Pull button turns blue with a ⬇ icon when the remote has new commits. This is checked automatically on startup and every 5 minutes.

Any error — including merge conflicts — aborts cleanly and shows a dialog. Nothing is auto-resolved.

---

## Requirements

- Anki **2.1.50** or later
- [CrowdAnki](https://ankiweb.net/shared/info/1788670778) add-on installed
- A local clone of your CrowdAnki git repository with SSH already configured — GitDeck uses the system `git` binary and does not manage authentication

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
| `repo_path` | Absolute path to the folder inside your git repository that contains the CrowdAnki deck files |
| `deck_name` | Exact deck name as shown in Anki, including `::` for sub-decks (e.g. `Japanese::Core 2000`) |

---

## Usage

Once configured, use the **GitDeck Pull** and **GitDeck Push** buttons in the top toolbar, or find the same actions under **Tools → Pull & Import** and **Tools → Export & Push**.

**Pulling** fetches the latest changes, imports the deck, and removes any notes that no longer exist in the shared repo. A tooltip confirms how many notes were added, updated, or deleted.

**Pushing** exports the current state of the deck and commits it. If nothing has changed since the last export, the commit step is skipped.

---

## Contributing & local testing

### Project layout

```
GitDeck/
├── __init__.py   # all add-on logic
├── config.json   # default config (both fields empty)
├── config.md     # shown in Anki's built-in config editor
├── icon.svg      # add-on manager icon
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

3. **Install CrowdAnki** (required at runtime) via Anki's add-on browser (id `1788670778`) or from [its GitHub repo](https://github.com/Apehaenger/CrowdAnki).

4. **Restart Anki.** You should see **GitDeck Pull** and **GitDeck Push** in the top toolbar.
 → export and import both work correctly

### Viewing add-on errors

- **macOS / Linux**: run Anki from the terminal — Python tracebacks print to stdout.
- **Windows**: use **Help → Open debug console** or start `anki.exe` from a terminal.

### Releasing a new version

1. Bump `human_version` in `manifest.json`.
2. Zip the contents of the `GitDeck/` directory (**not** the directory itself):
   ```bash
   cd GitDeck
   zip -r ../gitdeck.ankiaddon __init__.py config.json config.md icon.svg manifest.json
   ```
3. Upload `gitdeck.ankiaddon` to AnkiWeb.

---

## License

GNU AGPLv3
