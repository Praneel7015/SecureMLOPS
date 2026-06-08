from __future__ import annotations

import argparse
import json
import logging
import sqlite3
from pathlib import Path

from training.config import (
    DATASET_REGISTRY_PATH,
    DRIFT_BASELINE_DIR,
    DRIFT_EVENTS_PATH,
    JOB_REGISTRY_PATH,
    MODEL_REGISTRY_PATH,
    TRAINED_MODELS_DIR,
    TRAINING_STATE_DIR,
    ensure_training_dirs,
)

BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
DATASET_UPLOADS_DIR = UPLOADS_DIR / "datasets"
MODEL_UPLOADS_DIR = UPLOADS_DIR / "models"
SECURITY_EVENTS_DB = TRAINING_STATE_DIR / "security_events.db"
SECURITY_LOG_PATH = BASE_DIR / "logs" / "security.log"
BANS_PATH = BASE_DIR / "logs" / "bans.json"

logger = logging.getLogger("secureml.clear")


def _load_json(path: Path, root_key: str | None = None) -> dict:
    if not path.exists():
        return {root_key: {}} if root_key else {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        payload = {}
    if root_key and root_key not in payload:
        payload[root_key] = {}
    return payload


def _write_json(path: Path, payload: dict, dry_run: bool) -> None:
    if dry_run:
        print(f"[dry-run] Write {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _remove_path(path: Path, dry_run: bool, label: str | None = None) -> None:
    if not path.exists():
        return
    target = label or str(path)
    if dry_run:
        print(f"[dry-run] Remove {target}")
        return
    if path.is_dir():
        import shutil

        shutil.rmtree(path, ignore_errors=True)
    else:
        path.unlink(missing_ok=True)
    print(f"Removed {target}")


def _filter_registry(payload: dict, root_key: str, owner: str) -> tuple[dict, dict]:
    entries = payload.get(root_key, {})
    keep: dict = {}
    remove: dict = {}
    for key, value in entries.items():
        if value.get("owner") == owner:
            remove[key] = value
        else:
            keep[key] = value
    return {root_key: keep}, remove


def _dataset_upload_root(dataset: dict) -> Path | None:
    dataset_dir = dataset.get("dataset_dir")
    if not dataset_dir:
        dataset_id = dataset.get("dataset_id")
        if dataset_id:
            return DATASET_UPLOADS_DIR / str(dataset_id)
        return None

    path = Path(str(dataset_dir))
    if path.name == "dataset" and path.parent.exists():
        return path.parent
    if path.exists():
        return path
    dataset_id = dataset.get("dataset_id")
    if dataset_id:
        return DATASET_UPLOADS_DIR / str(dataset_id)
    return None


def clear_security_events(owner: str, dry_run: bool) -> int:
    if not SECURITY_EVENTS_DB.exists():
        return 0

    with sqlite3.connect(str(SECURITY_EVENTS_DB)) as conn:
        count = conn.execute(
            """
            SELECT COUNT(*)
            FROM security_events
            WHERE json_extract(metadata_json, '$.owner') = ?
            """,
            (owner,),
        ).fetchone()[0]
        if dry_run:
            print(f"[dry-run] Delete {count} security event(s) for user {owner}")
            return int(count)

        conn.execute(
            "DELETE FROM security_events WHERE json_extract(metadata_json, '$.owner') = ?",
            (owner,),
        )
        conn.commit()
    print(f"Deleted {count} security event(s) for user {owner}")
    return int(count)


def clear_drift_events(owner: str, dry_run: bool) -> int:
    if not DRIFT_EVENTS_PATH.exists():
        return 0

    payload = _load_json(DRIFT_EVENTS_PATH)
    events = payload.get("events", [])
    if not isinstance(events, list):
        events = []

    kept = [event for event in events if event.get("owner") != owner]
    removed = len(events) - len(kept)
    if dry_run:
        print(f"[dry-run] Remove {removed} drift event(s) for user {owner}")
        return removed

    payload["events"] = kept
    _write_json(DRIFT_EVENTS_PATH, payload, dry_run=False)
    print(f"Removed {removed} drift event(s) for user {owner}")
    return removed


def clear_training_registries(owner: str, dry_run: bool) -> dict[str, int]:
    ensure_training_dirs()

    datasets_payload = _load_json(DATASET_REGISTRY_PATH, "datasets")
    models_payload = _load_json(MODEL_REGISTRY_PATH, "models")
    jobs_payload = _load_json(JOB_REGISTRY_PATH, "jobs")

    datasets_payload, datasets_removed = _filter_registry(datasets_payload, "datasets", owner)
    models_payload, models_removed = _filter_registry(models_payload, "models", owner)
    jobs_payload, jobs_removed = _filter_registry(jobs_payload, "jobs", owner)

    for dataset in datasets_removed.values():
        upload_root = _dataset_upload_root(dataset)
        if upload_root:
            _remove_path(upload_root, dry_run, f"dataset upload {upload_root.name}")

    for model in models_removed.values():
        model_path = model.get("file_path")
        if model_path:
            _remove_path(Path(str(model_path)), dry_run, f"trained model {Path(str(model_path)).name}")

        baseline_path = model.get("drift_baseline_path")
        if baseline_path:
            _remove_path(Path(str(baseline_path)), dry_run, f"drift baseline {Path(str(baseline_path)).name}")

        embedded = model.get("drift_baseline")
        if isinstance(embedded, dict):
            embedded_path = embedded.get("path") or embedded.get("baseline_path")
            if embedded_path:
                _remove_path(Path(str(embedded_path)), dry_run, f"embedded drift baseline {embedded_path}")

    if dry_run:
        print(
            f"[dry-run] Registry removals for {owner}: "
            f"{len(datasets_removed)} dataset(s), "
            f"{len(models_removed)} model(s), "
            f"{len(jobs_removed)} job(s)"
        )
    else:
        _write_json(DATASET_REGISTRY_PATH, datasets_payload, dry_run=False)
        _write_json(MODEL_REGISTRY_PATH, models_payload, dry_run=False)
        _write_json(JOB_REGISTRY_PATH, jobs_payload, dry_run=False)
        print(
            f"Cleared training registries for {owner}: "
            f"{len(datasets_removed)} dataset(s), "
            f"{len(models_removed)} model(s), "
            f"{len(jobs_removed)} job(s)"
        )

    return {
        "datasets": len(datasets_removed),
        "models": len(models_removed),
        "jobs": len(jobs_removed),
    }


def clear_orphan_drift_baselines(owner: str, dry_run: bool) -> int:
    """Remove drift baseline files explicitly tagged with this owner."""
    removed = 0
    if not DRIFT_BASELINE_DIR.exists():
        return 0

    for baseline_file in DRIFT_BASELINE_DIR.glob("*.json"):
        try:
            payload = json.loads(baseline_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        if payload.get("owner") != owner:
            continue
        _remove_path(baseline_file, dry_run, f"drift baseline {baseline_file.name}")
        removed += 1
    return removed


def clear_access_analysis(owner: str, dry_run: bool) -> int:
    removed = 0
    try:
        from access_analysis.session_store import clear_session

        if dry_run:
            print(f"[dry-run] Clear in-memory access session for {owner}")
        else:
            clear_session(owner)
            print(f"Cleared in-memory access session for {owner}")
        removed += 1
    except Exception as exc:
        logger.warning("Could not clear access session: %s", exc)

    try:
        from access_analysis.db import _get_pool, _safe_table_identifier
        from psycopg2 import sql  # type: ignore

        pool = _get_pool()
        table_ident = _safe_table_identifier()
        if pool is None or table_ident is None:
            return removed

        query = sql.SQL("DELETE FROM {table} WHERE user_id = %s").format(table=table_ident)
        conn = None
        try:
            conn = pool.getconn()
            with conn.cursor() as cur:
                if dry_run:
                    count_query = sql.SQL(
                        "SELECT COUNT(*) FROM {table} WHERE user_id = %s"
                    ).format(table=table_ident)
                    cur.execute(count_query, (owner,))
                    count = int(cur.fetchone()[0])
                    print(f"[dry-run] Delete {count} access-analysis row(s) for {owner}")
                    return removed + count

                cur.execute(query, (owner,))
                deleted = cur.rowcount
            conn.commit()
            print(f"Deleted {deleted} access-analysis row(s) for {owner}")
            removed += deleted
        finally:
            if conn:
                pool.putconn(conn)
    except Exception as exc:
        logger.warning("Access-analysis DB cleanup skipped: %s", exc)

    return removed


def clear_rate_limit_state(owner: str, dry_run: bool) -> int:
    if not BANS_PATH.exists():
        return 0

    try:
        raw = json.loads(BANS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return 0

    prefix = f"{owner}:"
    kept = {key: value for key, value in raw.items() if not str(key).startswith(prefix)}
    removed = len(raw) - len(kept)
    if removed == 0:
        return 0

    if dry_run:
        print(f"[dry-run] Remove {removed} rate-limit ban(s) for {owner}")
        return removed

    if kept:
        BANS_PATH.write_text(json.dumps(kept, indent=2), encoding="utf-8")
    else:
        BANS_PATH.unlink(missing_ok=True)
    print(f"Removed {removed} rate-limit ban(s) for {owner}")
    return removed


def clear_security_log(owner: str, dry_run: bool) -> int:
    if not SECURITY_LOG_PATH.exists():
        return 0

    lines = SECURITY_LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
    kept: list[str] = []
    removed = 0
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except Exception:
            kept.append(line)
            continue
        if payload.get("user") == owner:
            removed += 1
            continue
        kept.append(line)

    if removed == 0:
        return 0

    if dry_run:
        print(f"[dry-run] Remove {removed} security.log line(s) for {owner}")
        return removed

    SECURITY_LOG_PATH.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    print(f"Removed {removed} security.log line(s) for {owner}")
    return removed


def clear_all_users(dry_run: bool) -> None:
    import shutil

    targets = [
        (UPLOADS_DIR, "uploads"),
        (TRAINED_MODELS_DIR, "trained models"),
        (TRAINING_STATE_DIR, "training state"),
        (DRIFT_BASELINE_DIR, "drift baselines"),
    ]
    for target, label in targets:
        if not target.exists():
            continue
        if dry_run:
            print(f"[dry-run] Remove all contents of {label}: {target}")
            continue
        for item in target.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink(missing_ok=True)
        print(f"Cleared {label}: {target}")

    for path, root_key in (
        (DATASET_REGISTRY_PATH, "datasets"),
        (MODEL_REGISTRY_PATH, "models"),
        (JOB_REGISTRY_PATH, "jobs"),
    ):
        _write_json(path, {root_key: {}}, dry_run)

    drift_payload = {"events": []}
    _write_json(DRIFT_EVENTS_PATH, drift_payload, dry_run)

    if SECURITY_EVENTS_DB.exists():
        if dry_run:
            print(f"[dry-run] Delete all rows from {SECURITY_EVENTS_DB}")
        else:
            with sqlite3.connect(str(SECURITY_EVENTS_DB)) as conn:
                conn.execute("DELETE FROM security_events")
                conn.commit()
            print(f"Cleared all security events from {SECURITY_EVENTS_DB}")

    _remove_path(BANS_PATH, dry_run, "rate-limit bans file")
    _remove_path(SECURITY_LOG_PATH, dry_run, "security log file")

    try:
        from access_analysis.session_store import _store

        if dry_run:
            print("[dry-run] Clear all in-memory access sessions")
        else:
            _store.clear()
            print("Cleared all in-memory access sessions")
    except Exception:
        pass

    print("Cleared all user-related platform data.")


def clear_user_data(owner: str, dry_run: bool = False) -> dict[str, int]:
    owner = owner.strip()
    if not owner:
        raise ValueError("Username is required.")

    print(f"{'[dry-run] ' if dry_run else ''}Clearing data for user: {owner}")

    summary = {}
    summary.update(clear_training_registries(owner, dry_run))
    summary["drift_events"] = clear_drift_events(owner, dry_run)
    summary["security_events"] = clear_security_events(owner, dry_run)
    summary["orphan_drift_baselines"] = clear_orphan_drift_baselines(owner, dry_run)
    summary["access_analysis"] = clear_access_analysis(owner, dry_run)
    summary["rate_limit_bans"] = clear_rate_limit_state(owner, dry_run)
    summary["security_log_lines"] = clear_security_log(owner, dry_run)

    print(f"Done. Summary for {owner}: {summary}")
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Remove platform data for a specific user (training, drift, telemetry, "
            "access analysis, rate limits) or wipe all users."
        )
    )
    parser.add_argument(
        "--user",
        type=str,
        help="Username whose datasets, models, jobs, drift logs, and telemetry should be removed.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Remove all users' training/drift/telemetry data (destructive).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be removed without deleting anything.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt when using --all.",
    )
    return parser


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = build_parser().parse_args()

    if args.all and args.user:
        raise SystemExit("Use either --user or --all, not both.")

    if args.all:
        if not args.yes and not args.dry_run:
            confirm = input("This will delete ALL users' data. Type 'yes' to continue: ")
            if confirm.strip().lower() != "yes":
                raise SystemExit("Aborted.")
        clear_all_users(args.dry_run)
        return

    if not args.user:
        raise SystemExit("Provide --user <username> or --all.")

    clear_user_data(args.user, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
