from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from training.config import (
    DATASET_REGISTRY_PATH,
    DATASETS_DIR,
    JOB_REGISTRY_PATH,
    MODEL_REGISTRY_PATH,
    TRAINED_MODELS_DIR,
    TRAINING_STATE_DIR,
    ensure_training_dirs,
)


def _reset_registry(path: Path, key: str, dry_run: bool) -> None:
    if dry_run:
        print(f"[dry-run] Reset {path} -> {{{key}: {{}}}}")
        return
    path.write_text(json.dumps({key: {}}, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Reset {path}")


def _clear_dir(target: Path, label: str, dry_run: bool) -> None:
    if not target.exists():
        if dry_run:
            print(f"[dry-run] {label} directory missing: {target}")
        return
    if dry_run:
        print(f"[dry-run] Remove contents of {label}: {target}")
        return
    for item in target.iterdir():
        if item.is_dir():
            shutil.rmtree(item, ignore_errors=True)
        else:
            item.unlink(missing_ok=True)
    print(f"Cleared {label}: {target}")


def _load_registry(path: Path, root_key: str) -> dict:
    if not path.exists():
        return {root_key: {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {root_key: {}}


def _filter_registry(payload: dict, root_key: str, owner: str) -> tuple[dict, dict]:
    entries = payload.get(root_key, {})
    keep = {}
    remove = {}
    for key, value in entries.items():
        if value.get("owner") == owner:
            remove[key] = value
        else:
            keep[key] = value
    return {root_key: keep}, remove


def clear_training_state(dry_run: bool, owner: str | None = None) -> None:
    ensure_training_dirs()
    if not owner:
        _clear_dir(DATASETS_DIR, "training datasets", dry_run)
        _clear_dir(TRAINED_MODELS_DIR, "trained models", dry_run)
        _clear_dir(TRAINING_STATE_DIR, "training state", dry_run)

        if dry_run:
            return

        _reset_registry(DATASET_REGISTRY_PATH, "datasets", dry_run)
        _reset_registry(MODEL_REGISTRY_PATH, "models", dry_run)
        _reset_registry(JOB_REGISTRY_PATH, "jobs", dry_run)
        return

    datasets_payload = _load_registry(DATASET_REGISTRY_PATH, "datasets")
    models_payload = _load_registry(MODEL_REGISTRY_PATH, "models")
    jobs_payload = _load_registry(JOB_REGISTRY_PATH, "jobs")

    datasets_payload, datasets_to_remove = _filter_registry(datasets_payload, "datasets", owner)
    models_payload, models_to_remove = _filter_registry(models_payload, "models", owner)
    jobs_payload, jobs_to_remove = _filter_registry(jobs_payload, "jobs", owner)

    for dataset in datasets_to_remove.values():
        dataset_dir = Path(dataset.get("dataset_dir", ""))
        if dataset_dir.exists():
            if dry_run:
                print(f"[dry-run] Remove dataset directory: {dataset_dir}")
            else:
                shutil.rmtree(dataset_dir, ignore_errors=True)

    for model in models_to_remove.values():
        model_path = Path(model.get("file_path", ""))
        if model_path.exists():
            if dry_run:
                print(f"[dry-run] Remove model file: {model_path}")
            else:
                model_path.unlink(missing_ok=True)

    if dry_run:
        print(f"[dry-run] Remove {len(jobs_to_remove)} jobs for user {owner}")
        return

    DATASET_REGISTRY_PATH.write_text(json.dumps(datasets_payload, indent=2, sort_keys=True), encoding="utf-8")
    MODEL_REGISTRY_PATH.write_text(json.dumps(models_payload, indent=2, sort_keys=True), encoding="utf-8")
    JOB_REGISTRY_PATH.write_text(json.dumps(jobs_payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Cleared training artifacts for user: {owner}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Clear training datasets, models, and registries for a clean run.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be removed without deleting anything.",
    )
    parser.add_argument(
        "--user",
        type=str,
        help="Clear only the specified user's datasets/models/jobs (keeps other users' data).",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    clear_training_state(args.dry_run, owner=args.user)


if __name__ == "__main__":
    main()
