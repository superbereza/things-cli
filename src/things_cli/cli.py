#!/usr/bin/env python3
"""Things 3 CLI — based on things-mcp by hald.

Read operations use the things.py library (direct SQLite).
Write operations use the Things URL scheme via osascript.
"""
import argparse
import json
import re
import subprocess
import sys
import time
import urllib.parse
from typing import Any, Dict, Iterable, List, Optional

__version__ = "1.1.0"

# ---------------------------------------------------------------------------
# things.py — optional dependency for reads & for fetching the auth token.
# ---------------------------------------------------------------------------
try:
    import things
    HAS_THINGS_LIB = True
except ImportError:
    HAS_THINGS_LIB = False


# Things 3 stores UUIDs as 22-char base62 strings (e.g. "3aEmFg6pBm1Vihy5DofYdR").
UUID_RE = re.compile(r"^[A-Za-z0-9]{22}$")


def is_uuid(s: Optional[str]) -> bool:
    return bool(s and UUID_RE.match(s))


def die(msg: str, code: str = "error") -> None:
    """Print structured error to stdout, exit 1."""
    print(json.dumps({"status": "error", "code": code, "message": msg},
                     ensure_ascii=False))
    sys.exit(1)


def print_json(payload: Any, pretty: bool = False) -> None:
    print(json.dumps(payload, ensure_ascii=False,
                     indent=2 if pretty else None))


# ============================================================================
# URL Scheme (write operations)
# ============================================================================

def execute_url(url: str) -> None:
    """Open a things:// URL via osascript (no app focus stealing)."""
    try:
        subprocess.run(
            ["osascript", "-e", f'tell application "Things3" to open location "{url}"'],
            check=True, capture_output=True, text=True,
        )
    except subprocess.CalledProcessError:
        import webbrowser
        webbrowser.open(url)


def construct_url(command: str, params: Dict[str, Any]) -> str:
    """Build a things:// URL from command + params."""
    url = f"things:///{command}"

    # Auto-attach auth token for update operations
    if command in ("update", "update-project") and HAS_THINGS_LIB:
        token = things.token()
        if token:
            params = {**params, "auth-token": token}

    encoded = []
    for k, v in params.items():
        if v is None:
            continue
        if isinstance(v, bool):
            v = str(v).lower()
        elif isinstance(v, list):
            v = ",".join(str(x) for x in v)
        encoded.append(f"{k}={urllib.parse.quote(str(v))}")
    if encoded:
        url += "?" + "&".join(encoded)
    return url


def _split_list_param(params: Dict[str, Any], key: str = "list") -> None:
    """In-place: convert {key: 'value'} to {key-id: uuid} if value looks like a UUID."""
    val = params.get(key)
    if val is None:
        return
    if is_uuid(val):
        params.pop(key)
        params[f"{key}-id"] = val


# ============================================================================
# Verification helper (--wait)
# ============================================================================

def poll_for_new_uuid(
    title: str,
    before_uuids: Iterable[str],
    timeout_s: float = 3.0,
    interval_s: float = 0.2,
) -> Optional[str]:
    """Wait until a todo with matching title and a NEW uuid appears."""
    if not HAS_THINGS_LIB:
        return None
    before = set(before_uuids)
    target = (title or "").strip()
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        for t in (things.search(target) or []):
            if t["uuid"] in before:
                continue
            if (t.get("title") or "").strip() == target:
                return t["uuid"]
        time.sleep(interval_s)
    return None


def snapshot_uuids_for_title(title: str) -> List[str]:
    """Capture uuids of existing todos matching title (for --wait delta)."""
    if not HAS_THINGS_LIB:
        return []
    target = (title or "").strip()
    return [t["uuid"] for t in (things.search(target) or [])
            if (t.get("title") or "").strip() == target]


# ============================================================================
# Formatters (read output)
# ============================================================================

def format_todo(todo: dict) -> dict:
    result = {
        "uuid": todo.get("uuid"),
        "title": todo.get("title"),
        "type": todo.get("type"),
        "status": todo.get("status"),
    }
    for src, dst in (("notes", "notes"), ("start", "list"),
                     ("start_date", "start_date"), ("deadline", "deadline"),
                     ("tags", "tags"), ("checklist", "checklist")):
        v = todo.get(src)
        if v:
            result[dst] = v
    # Resolve project/area names
    if todo.get("project") and HAS_THINGS_LIB:
        try:
            proj = things.get(todo["project"])
            if proj:
                result["project"] = proj["title"]
                result["project_uuid"] = todo["project"]
        except Exception:
            pass
    if todo.get("area") and HAS_THINGS_LIB:
        try:
            ar = things.get(todo["area"])
            if ar:
                result["area"] = ar["title"]
                result["area_uuid"] = todo["area"]
        except Exception:
            pass
    return result


def format_project(project: dict, include_items: bool = False) -> dict:
    result = {
        "uuid": project.get("uuid"),
        "title": project.get("title"),
        "type": "project",
    }
    if project.get("notes"):
        result["notes"] = project["notes"]
    if project.get("area") and HAS_THINGS_LIB:
        try:
            ar = things.get(project["area"])
            if ar:
                result["area"] = ar["title"]
                result["area_uuid"] = project["area"]
        except Exception:
            pass
    if include_items and HAS_THINGS_LIB:
        todos = things.todos(project=project["uuid"]) or []
        result["tasks"] = [t["title"] for t in todos]
    return result


def apply_read_filters(items: list, args: argparse.Namespace,
                        field: str = "title") -> list:
    """Apply --grep / --limit common to read commands."""
    grep = getattr(args, "grep", None)
    if grep:
        gp = grep.lower()
        items = [it for it in items if gp in ((it.get(field) or "").lower())]
    limit = getattr(args, "limit", None)
    if limit and limit > 0:
        items = items[:limit]
    return items


# ============================================================================
# Read commands
# ============================================================================

def _require_lib() -> None:
    if not HAS_THINGS_LIB:
        die("things.py library not installed — run install.sh to set up venv",
            code="MISSING_LIB")


def cmd_inbox(args):
    _require_lib()
    out = [format_todo(t) for t in (things.inbox(include_items=True) or [])]
    print_json(apply_read_filters(out, args), args.pretty)


def cmd_today(args):
    _require_lib()
    out = [format_todo(t) for t in (things.today(include_items=True) or [])]
    print_json(apply_read_filters(out, args), args.pretty)


def cmd_upcoming(args):
    _require_lib()
    out = [format_todo(t) for t in (things.upcoming(include_items=True) or [])]
    print_json(apply_read_filters(out, args), args.pretty)


def cmd_anytime(args):
    _require_lib()
    out = [format_todo(t) for t in (things.anytime(include_items=True) or [])]
    print_json(apply_read_filters(out, args), args.pretty)


def cmd_someday(args):
    _require_lib()
    out = [format_todo(t) for t in (things.someday(include_items=True) or [])]
    print_json(apply_read_filters(out, args), args.pretty)


def cmd_projects(args):
    _require_lib()
    out = [format_project(p, args.items) for p in (things.projects() or [])]
    print_json(apply_read_filters(out, args), args.pretty)


def cmd_areas(args):
    _require_lib()
    out = []
    for area in (things.areas() or []):
        a = {"uuid": area["uuid"], "title": area["title"]}
        if args.items:
            projects = things.projects(area=area["uuid"]) or []
            a["projects"] = [p["title"] for p in projects]
        out.append(a)
    print_json(apply_read_filters(out, args), args.pretty)


def cmd_tags(args):
    _require_lib()
    out = [{"uuid": t["uuid"], "title": t["title"]}
           for t in (things.tags() or [])]
    print_json(apply_read_filters(out, args), args.pretty)


def cmd_search(args):
    _require_lib()
    out = [format_todo(t)
           for t in (things.search(args.query, include_items=True) or [])]
    # apply --limit only (grep doesn't compose with explicit search query)
    limit = getattr(args, "limit", None)
    if limit and limit > 0:
        out = out[:limit]
    print_json(out, args.pretty)


# ============================================================================
# Write commands
# ============================================================================

def _todo_params(item: dict) -> Dict[str, Any]:
    """Map our normalized todo dict to Things URL scheme params."""
    params: Dict[str, Any] = {"title": item.get("title")}
    for src, dst in (("notes", "notes"), ("when", "when"),
                     ("deadline", "deadline"), ("tags", "tags"),
                     ("list", "list")):
        if item.get(src):
            params[dst] = item[src]
    if item.get("checklist"):
        params["checklist-items"] = "\n".join(item["checklist"])
    _split_list_param(params, "list")
    return params


def _parse_stdin_items(raw: str) -> List[dict]:
    """Parse stdin as JSON array OR NDJSON (one JSON object per line)."""
    raw = raw.strip()
    if not raw:
        return []
    if raw.startswith("["):
        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            raise ValueError("expected a JSON array")
        return parsed
    items = []
    for ln in raw.split("\n"):
        ln = ln.strip()
        if not ln:
            continue
        items.append(json.loads(ln))
    return items


def _add_one(item: dict, wait: bool) -> Dict[str, Any]:
    title = item.get("title")
    if not title:
        return {"status": "error", "code": "MISSING_TITLE",
                "message": "item has no title", "item": item}
    before = snapshot_uuids_for_title(title) if wait else []
    execute_url(construct_url("add", _todo_params(item)))
    out: Dict[str, Any] = {"status": "ok", "title": title}
    if wait:
        uuid = poll_for_new_uuid(title, before)
        if uuid:
            out["uuid"] = uuid
        else:
            out["status"] = "pending"
            out["message"] = "URL fired but new todo didn't appear within timeout"
    return out


def cmd_add(args):
    if args.stdin:
        try:
            items = _parse_stdin_items(sys.stdin.read())
        except (json.JSONDecodeError, ValueError) as e:
            die(f"failed to parse stdin: {e}", code="BAD_INPUT")
        if not items:
            die("stdin had no items", code="EMPTY_INPUT")
        results = [_add_one(it, args.wait) for it in items]
        print_json(results, args.pretty)
        return

    if not args.title:
        die("title is required (or pass --stdin for batch)", code="MISSING_TITLE")

    item = {
        "title": args.title,
        "notes": args.notes,
        "when": args.when,
        "deadline": args.deadline,
        "tags": args.tags,
        "list": args.list,
        "checklist": args.checklist,
    }
    print_json(_add_one(item, args.wait), args.pretty)


def cmd_add_project(args):
    params: Dict[str, Any] = {"title": args.title}
    for src in ("notes", "when", "deadline", "tags", "area"):
        v = getattr(args, src, None)
        if v:
            params[src] = v
    if args.todos:
        params["to-dos"] = "\n".join(args.todos)
    _split_list_param(params, "area")
    execute_url(construct_url("add-project", params))
    print_json({"status": "ok", "title": args.title}, args.pretty)


def _validate_uuids(uuids: List[str]) -> None:
    """Fail fast on malformed UUIDs (incl. accidental space-joined args)."""
    for u in uuids:
        if not is_uuid(u):
            preview = u if len(u) < 80 else u[:77] + "..."
            die(f'invalid Things UUID: "{preview}" — '
                f'expected a 22-char alphanumeric string. '
                f'If passing multiple UUIDs from a shell variable, do not quote: '
                f'`things complete $uuids`, not `things complete "$uuids"`.',
                code="INVALID_UUID")


def cmd_complete(args):
    _require_lib()  # for auth token
    _validate_uuids(args.uuid)
    results = []
    for uuid in args.uuid:
        execute_url(construct_url("update", {"id": uuid, "completed": True}))
        results.append({"status": "ok", "uuid": uuid, "completed": True})
    # Single-uuid → single object; multi-uuid → array (more agent-friendly).
    print_json(results[0] if len(results) == 1 else results, args.pretty)


def cmd_cancel(args):
    _require_lib()
    _validate_uuids(args.uuid)
    results = []
    for uuid in args.uuid:
        execute_url(construct_url("update", {"id": uuid, "canceled": True}))
        results.append({"status": "ok", "uuid": uuid, "canceled": True})
    print_json(results[0] if len(results) == 1 else results, args.pretty)


def cmd_update(args):
    _require_lib()
    _validate_uuids([args.uuid])
    params: Dict[str, Any] = {"id": args.uuid}
    if args.title:
        params["title"] = args.title
    if args.notes:
        params["notes"] = args.notes
    if args.when:
        params["when"] = args.when
    if args.deadline:
        params["deadline"] = args.deadline
    if args.tags:
        params["tags"] = args.tags
    if args.list:
        # Things URL scheme update accepts list-id (UUID).
        # Resolve a name to UUID via things.py if needed.
        if is_uuid(args.list):
            params["list-id"] = args.list
        else:
            target = args.list.strip()
            match = next((p for p in (things.projects() or [])
                          if (p.get("title") or "").strip() == target), None)
            if not match:
                match = next((a for a in (things.areas() or [])
                              if (a.get("title") or "").strip() == target), None)
            if not match:
                die(f'no project/area named "{args.list}"',
                    code="DESTINATION_NOT_FOUND")
            params["list-id"] = match["uuid"]
    execute_url(construct_url("update", params))
    print_json({"status": "ok", "uuid": args.uuid}, args.pretty)


def cmd_tag_add(args):
    _require_lib()
    _validate_uuids([args.uuid])
    todo = things.get(args.uuid)
    if not todo:
        die(f"todo not found: {args.uuid}", code="NOT_FOUND")
    current = set(todo.get("tags") or [])
    new = current | set(args.tags)
    execute_url(construct_url(
        "update", {"id": args.uuid, "tags": ",".join(sorted(new))}))
    print_json({"status": "ok", "uuid": args.uuid, "tags": sorted(new)},
               args.pretty)


def cmd_tag_remove(args):
    _require_lib()
    _validate_uuids([args.uuid])
    todo = things.get(args.uuid)
    if not todo:
        die(f"todo not found: {args.uuid}", code="NOT_FOUND")
    current = set(todo.get("tags") or [])
    new = current - set(args.tags)
    execute_url(construct_url(
        "update", {"id": args.uuid, "tags": ",".join(sorted(new))}))
    print_json({"status": "ok", "uuid": args.uuid, "tags": sorted(new)},
               args.pretty)


def cmd_show(args):
    params: Dict[str, Any] = {"id": args.id}
    if args.query:
        params["query"] = args.query
    execute_url(construct_url("show", params))
    print_json({"status": "ok", "showing": args.id}, args.pretty)


# ============================================================================
# Doctor (env diagnostic)
# ============================================================================

def cmd_doctor(args):
    checks = []

    # 1. things.py library
    if HAS_THINGS_LIB:
        try:
            ver = getattr(things, "__version__", "unknown")
        except Exception:
            ver = "unknown"
        checks.append({"check": "things.py library", "status": "ok",
                       "detail": f"version {ver}"})
    else:
        checks.append({"check": "things.py library", "status": "missing",
                       "detail": "pip install things.py — read ops won't work"})

    # 2. Things 3 app reachable via osascript
    try:
        r = subprocess.run(
            ["osascript", "-e", 'tell application "Things3" to return version'],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            checks.append({"check": "Things 3 app", "status": "ok",
                           "detail": f"version {r.stdout.strip()}"})
        else:
            checks.append({"check": "Things 3 app", "status": "unreachable",
                           "detail": (r.stderr or "").strip() or "no response"})
    except Exception as e:
        checks.append({"check": "Things 3 app", "status": "error",
                       "detail": str(e)})

    # 3. SQLite read access
    if HAS_THINGS_LIB:
        try:
            n = len(things.inbox() or [])
            checks.append({"check": "SQLite read access", "status": "ok",
                           "detail": f"reads work — {n} inbox items"})
        except Exception as e:
            checks.append({"check": "SQLite read access", "status": "error",
                           "detail": str(e)})

    # 4. Auth token (needed for update/complete/cancel/tag-*)
    if HAS_THINGS_LIB:
        try:
            token = things.token()
            if token:
                checks.append({"check": "Auth token", "status": "ok",
                               "detail": f"{len(token)}-char token available"})
            else:
                checks.append({"check": "Auth token", "status": "missing",
                               "detail": ('enable in Things → Settings → General '
                                          '→ "Enable Things URLs"')})
        except Exception as e:
            checks.append({"check": "Auth token", "status": "error",
                           "detail": str(e)})

    overall_ok = all(c["status"] == "ok" for c in checks)
    if args.pretty:
        sym = {"ok": "✓", "missing": "⚠", "error": "✗", "unreachable": "✗"}
        for c in checks:
            print(f"  {sym.get(c['status'], '?')} "
                  f"{c['check']:24} {c['status']:12} {c['detail']}")
        print()
        print(f"Overall: {'ALL OK' if overall_ok else 'ISSUES FOUND'}")
    else:
        print_json({"overall": "ok" if overall_ok else "issues",
                    "checks": checks})
    sys.exit(0 if overall_ok else 1)


# ============================================================================
# main / parsers
# ============================================================================

def main():
    # Shared --pretty on every subcommand (git-style: `things <cmd> --pretty`)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--pretty", "-p", action="store_true",
                        help="Pretty print JSON")

    # Read commands additionally get --grep / --limit
    read_common = argparse.ArgumentParser(add_help=False, parents=[common])
    read_common.add_argument("--grep", "-g",
                             help="Case-insensitive substring filter on title")
    read_common.add_argument("--limit", type=int,
                             help="Max items to return (default: no limit)")

    parser = argparse.ArgumentParser(
        description="Things 3 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  things today --pretty
  things projects --items --grep "mac"
  things search "meeting" --limit 5
  things add "Buy milk" --when today --tags shopping --wait
  echo '[{"title":"T1"},{"title":"T2","deadline":"2026-07-01"}]' \\
      | things add --stdin --wait
  things add-project "New project" --area "Home" \\
      --todos "Step 1" --todos "Step 2"
  things complete UUID1 UUID2 UUID3
  things update UUID --list "Other Project"
  things tag-add UUID urgent important
  things tag-remove UUID someday
  things cancel UUID
  things show today
  things doctor --pretty
""",
    )
    parser.add_argument("--version", action="version",
                        version=f"things-cli {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    def sub(name, **kwargs):
        return subparsers.add_parser(name, parents=[common], **kwargs)

    def sub_r(name, **kwargs):
        return subparsers.add_parser(name, parents=[read_common], **kwargs)

    # ------------------- read -------------------
    sub_r("inbox", help="Get inbox todos").set_defaults(func=cmd_inbox)
    sub_r("today", help="Get today todos").set_defaults(func=cmd_today)
    sub_r("upcoming", help="Get upcoming todos").set_defaults(func=cmd_upcoming)
    sub_r("anytime", help="Get anytime todos").set_defaults(func=cmd_anytime)
    sub_r("someday", help="Get someday todos").set_defaults(func=cmd_someday)

    sp = sub_r("projects", help="Get all projects")
    sp.add_argument("--items", "-i", action="store_true",
                    help="Include each project's task titles")
    sp.set_defaults(func=cmd_projects)

    sp = sub_r("areas", help="Get all areas")
    sp.add_argument("--items", "-i", action="store_true",
                    help="Include each area's projects")
    sp.set_defaults(func=cmd_areas)

    sub_r("tags", help="Get all tags").set_defaults(func=cmd_tags)

    sp = sub_r("search", help="Search todos by title/notes substring")
    sp.add_argument("query", help="Search query")
    sp.set_defaults(func=cmd_search)

    # ------------------- write ------------------
    sp = sub("add", help="Add a todo (or many via --stdin)")
    sp.add_argument("title", nargs="?",
                    help="Todo title (omit when using --stdin)")
    sp.add_argument("--notes", "-n", help="Notes / description")
    sp.add_argument("--when", "-w",
                    help="When: today | tomorrow | evening | anytime | someday | YYYY-MM-DD")
    sp.add_argument("--deadline", "-d", help="Deadline: YYYY-MM-DD")
    sp.add_argument("--tags", "-t", help="Comma-separated tags")
    sp.add_argument("--list", "-l",
                    help="Destination project/area (name OR UUID — auto-detected)")
    sp.add_argument("--checklist", "-c", action="append",
                    help="Checklist item (repeat the flag for multiple)")
    sp.add_argument("--stdin", action="store_true",
                    help="Read items from stdin (JSON array or NDJSON)")
    sp.add_argument("--wait", action="store_true",
                    help="Poll SQLite after write to return the real UUID(s)")
    sp.set_defaults(func=cmd_add)

    sp = sub("add-project", help="Add a project")
    sp.add_argument("title", help="Project title")
    sp.add_argument("--notes", "-n", help="Notes")
    sp.add_argument("--when", "-w", help="When to start")
    sp.add_argument("--deadline", "-d", help="Deadline")
    sp.add_argument("--tags", "-t", help="Comma-separated tags")
    sp.add_argument("--area", "-a",
                    help="Destination area (name OR UUID — auto-detected)")
    sp.add_argument("--todos", action="append",
                    help="Initial todo (repeat the flag for multiple)")
    sp.set_defaults(func=cmd_add_project)

    sp = sub("complete", help="Mark todo(s) as completed")
    sp.add_argument("uuid", nargs="+", help="Todo UUID(s)")
    sp.set_defaults(func=cmd_complete)

    sp = sub("cancel", help="Mark todo(s) as canceled (✗, not done)")
    sp.add_argument("uuid", nargs="+", help="Todo UUID(s)")
    sp.set_defaults(func=cmd_cancel)

    sp = sub("update", help="Update an existing todo")
    sp.add_argument("uuid", help="Todo UUID")
    sp.add_argument("--title", help="New title")
    sp.add_argument("--notes", "-n", help="New notes")
    sp.add_argument("--when", "-w", help="New 'when'")
    sp.add_argument("--deadline", "-d", help="New deadline")
    sp.add_argument("--tags", "-t",
                    help="REPLACE tags (comma-separated). Use tag-add/tag-remove for delta.")
    sp.add_argument("--list", "-l",
                    help="Move to project/area (name OR UUID — auto-resolved)")
    sp.set_defaults(func=cmd_update)

    sp = sub("tag-add", help="Add tag(s) to a todo (preserves existing tags)")
    sp.add_argument("uuid", help="Todo UUID")
    sp.add_argument("tags", nargs="+", help="Tag(s) to add")
    sp.set_defaults(func=cmd_tag_add)

    sp = sub("tag-remove", help="Remove tag(s) from a todo (preserves the rest)")
    sp.add_argument("uuid", help="Todo UUID")
    sp.add_argument("tags", nargs="+", help="Tag(s) to remove")
    sp.set_defaults(func=cmd_tag_remove)

    sp = sub("show", help="Open something in the Things app UI")
    sp.add_argument(
        "id",
        help="Item UUID or smart-list: inbox | today | upcoming | anytime | someday | logbook | trash")
    sp.add_argument("--query", "-q", help="Filter query within that list")
    sp.set_defaults(func=cmd_show)

    sub("doctor", help="Diagnose installation (Things app, library, auth token)") \
        .set_defaults(func=cmd_doctor)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
