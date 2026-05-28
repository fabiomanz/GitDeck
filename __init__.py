"""
GitDeck - sync an Anki deck with a CrowdAnki git repository.

Tools menu items
  • Pull & Import  - git pull, then CrowdAnki import
  • Export & Push  - CrowdAnki export, then git add/commit/push

All git/network I/O runs off the UI thread via aqt.operations.QueryOp.
Collection access (CrowdAnki import/export) runs on the main thread.
Any error is shown in a dialog; nothing is auto-resolved.
"""

import importlib
import json
import subprocess
from datetime import datetime
from pathlib import Path

from aqt import gui_hooks, mw
from aqt.operations import QueryOp
from aqt.qt import QAction, QMessageBox, QTimer
from aqt.utils import tooltip

# AnkiWeb numeric ID for the CrowdAnki add-on.
_CA = "1788670778"

# Inline version of icon.svg for the toolbar Pull button (inherits parent colour).
_DOWN_ARROW = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="11" height="11" '
    'fill="none" stroke="currentColor" stroke-width="2.2" '
    'stroke-linecap="round" stroke-linejoin="round" '
    'style="vertical-align:middle;margin-right:3px;">'
    '<line x1="8" y1="3.5" x2="8" y2="10"/>'
    '<polyline points="5.5,7.5 8,10 10.5,7.5"/>'
    '<line x1="5" y1="12.5" x2="11" y2="12.5"/>'
    '</svg>'
)

# True when the remote has commits the local repo does not.
_has_remote_updates = False


# ── helpers ───────────────────────────────────────────────────────────────────

def _cfg():
    raw = mw.addonManager.getConfig(__name__) or {}
    return raw.get("repo_path", "").strip(), raw.get("deck_name", "").strip()


def _err(title: str, body) -> None:
    QMessageBox.critical(mw, f"GitDeck – {title}", str(body))


def _ca(submodule: str):
    """Import a submodule from the installed CrowdAnki package by numeric ID."""
    return importlib.import_module(f"{_CA}.{submodule}")


def _git(args: list, cwd: str) -> str:
    """Run a git sub-command; raise RuntimeError on non-zero exit."""
    r = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or r.stdout.strip())
    return r.stdout.strip()


# ── Remote update check ────────────────────────────────────────────────────────

def _check_remote() -> None:
    """Fetch remote refs and turn the Pull button blue if updates exist."""
    repo_path, _ = _cfg()
    if not repo_path:
        return

    def worker() -> bool:
        try:
            subprocess.run(
                ["git", "fetch"],
                cwd=repo_path,
                capture_output=True,
                timeout=30,
            )
            r = subprocess.run(
                ["git", "rev-list", "HEAD..@{u}", "--count"],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )
            return r.returncode == 0 and int(r.stdout.strip() or "0") > 0
        except Exception:
            return False

    def on_done(fut) -> None:
        global _has_remote_updates
        try:
            has_updates = fut.result()
        except Exception:
            return
        if has_updates != _has_remote_updates:
            _has_remote_updates = has_updates
            mw.toolbar.draw()

    mw.taskman.run_in_background(worker, on_done)


# ── Deletion of notes removed from the repo ───────────────────────────────────

def _collect_guids(deck_json: dict) -> set:
    """Recursively collect all note GUIDs from a CrowdAnki deck JSON tree."""
    guids = {note["guid"] for note in deck_json.get("notes", [])}
    for child in deck_json.get("children", []):
        guids |= _collect_guids(child)
    return guids


def _delete_removed_notes(repo_path: str, deck_name: str) -> int:
    """Delete notes that exist in the collection but are absent from the repo JSON.

    CrowdAnki's importer only adds/updates — it never removes. This fills that gap.
    Returns the number of notes deleted.
    """
    repo = Path(repo_path)
    # Mirror CrowdAnki's own file-discovery logic.
    json_path = repo / "deck.json"
    if not json_path.exists():
        json_path = repo / (repo.name + ".json")
    if not json_path.exists():
        return 0

    with json_path.open(encoding="utf8") as f:
        json_guids = _collect_guids(json.load(f))

    # find_notes with deck: includes all sub-decks automatically.
    note_ids = mw.col.find_notes(f'deck:"{deck_name}"')
    to_delete = [nid for nid in note_ids if mw.col.get_note(nid).guid not in json_guids]

    if to_delete:
        mw.col.remove_notes(to_delete)

    return len(to_delete)


# ── Pull & Import ──────────────────────────────────────────────────────────────

def _pull_and_import() -> None:
    repo_path, deck_name = _cfg()
    if not repo_path or not deck_name:
        _err("Config missing", "Set repo_path and deck_name in the add-on config (Tools → Add-ons).")
        return

    def op(_col):
        _git(["pull"], cwd=repo_path)

    def on_success(_) -> None:
        global _has_remote_updates
        try:
            mod = _ca("importer.anki_importer")
            mod.AnkiJsonImporter(mw.col).load_deck(Path(repo_path))
            deleted = _delete_removed_notes(repo_path, deck_name)
            _has_remote_updates = False
            mw.toolbar.draw()
            msg = "GitDeck: pull & import complete."
            if deleted:
                msg += f" {deleted} note(s) deleted."
            tooltip(msg, period=4000)
        except Exception as exc:
            _err("Import error", exc)

    def on_failure(exc: Exception) -> None:
        _err("Git pull failed", exc)

    (
        QueryOp(parent=mw, op=op, success=on_success)
        .failure(on_failure)
        .with_progress("GitDeck: pulling…")
        .run_in_background()
    )


# ── Export & Push ──────────────────────────────────────────────────────────────

def _export_and_push() -> None:
    repo_path, deck_name = _cfg()
    if not repo_path or not deck_name:
        _err("Config missing", "Set repo_path and deck_name in the add-on config (Tools → Add-ons).")
        return

    # CrowdAnki export touches the collection - run on the main thread first.
    try:
        deck_dict = mw.col.decks.by_name(deck_name)
        if deck_dict is None:
            _err("Deck not found", f"No deck named {deck_name!r} exists in your collection.")
            return

        anki_deck_mod = _ca("anki.adapters.anki_deck")
        deck = anki_deck_mod.AnkiDeck(mw.col.decks.get(deck_dict["id"], default=False))

        if deck.is_dynamic:
            _err("Export error", "CrowdAnki does not support dynamic (filtered) decks.")
            return

        # Clean up duplicate note-model UUIDs before exporting.
        _ca("utils.disambiguate_uuids").disambiguate_note_model_uuids(mw.col)

        config = _ca("config.config_settings").ConfigSettings.get_instance()
        exporter = _ca("export.anki_exporter").AnkiJsonExporter(mw.col, config)
        exporter.export_to_directory(deck, Path(repo_path), copy_media=True, create_deck_subdirectory=False)

    except Exception as exc:
        _err("Export error", exc)
        return

    commit_msg = f"GitDeck Update {deck_name} – {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    def op(_col) -> str:
        _git(["add", repo_path], cwd=repo_path)

        r = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            combined = (r.stderr + r.stdout).lower()
            if "nothing to commit" in combined or "nothing added to commit" in combined:
                return "nothing_to_commit"
            raise RuntimeError(r.stderr.strip() or r.stdout.strip())

        _git(["push"], cwd=repo_path)
        return "ok"

    def on_success(result: str) -> None:
        if result == "nothing_to_commit":
            tooltip("GitDeck: deck unchanged – nothing committed.", period=3000)
        else:
            tooltip("GitDeck: export & push complete.", period=3000)

    def on_failure(exc: Exception) -> None:
        _err("Git push failed", exc)

    (
        QueryOp(parent=mw, op=op, success=on_success)
        .failure(on_failure)
        .with_progress("GitDeck: pushing…")
        .run_in_background()
    )


# ── Menu ───────────────────────────────────────────────────────────────────────

def _setup_menu() -> None:
    tools = mw.form.menuTools

    pull_action = QAction("Pull && Import", mw)
    pull_action.setStatusTip("git pull, then import deck via CrowdAnki")
    pull_action.triggered.connect(_pull_and_import)
    tools.addAction(pull_action)

    push_action = QAction("Export && Push", mw)
    push_action.setStatusTip("Export deck via CrowdAnki, then git add/commit/push")
    push_action.triggered.connect(_export_and_push)
    tools.addAction(push_action)


# ── Toolbar buttons ────────────────────────────────────────────────────────────

def _setup_toolbar(links: list, toolbar) -> None:
    # Register handlers directly – avoids using create_link's label for aria-label,
    # which would break the HTML when the label contains SVG/span markup.
    toolbar.link_handlers["gitdeck_pull"] = _pull_and_import
    toolbar.link_handlers["gitdeck_push"] = _export_and_push

    if _has_remote_updates:
        pull_content = f'{_DOWN_ARROW}GitDeck Pull'
        pull_style = ' style="color:#4c9be8"'
    else:
        pull_content = "GitDeck Pull"
        pull_style = ""

    links.append(
        f'<a class=hitem tabindex="-1" aria-label="GitDeck Pull" '
        f'title="GitDeck: git pull &amp; import" id="gitdeck_pull" '
        f'href=# onclick="return pycmd(\'gitdeck_pull\')"{pull_style}>'
        f"{pull_content}</a>"
    )
    links.append(
        '<a class=hitem tabindex="-1" aria-label="GitDeck Push" '
        'title="GitDeck: export &amp; git push" id="gitdeck_push" '
        "href=# onclick=\"return pycmd('gitdeck_push')\">"
        "GitDeck Push</a>"
    )


def _on_profile_open() -> None:
    """Force toolbar redraw so buttons appear, then kick off first remote check."""
    mw.toolbar.draw()
    _check_remote()
    timer = QTimer(mw)
    timer.timeout.connect(_check_remote)
    timer.start(5 * 60 * 1000)


gui_hooks.main_window_did_init.append(_setup_menu)
gui_hooks.top_toolbar_did_init_links.append(_setup_toolbar)
gui_hooks.profile_did_open.append(_on_profile_open)
