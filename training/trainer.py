from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import torch
from torch import nn
import torch.nn.functional as F
from torch.optim import Adam

from core.runtime import get_device
from training import progress_tracker
from training.config import SUPPORTED_MODELS
from training.dataset_loader import build_dataloaders, load_datasets
from training.exporter import export_model
from training.model_factory import build_model, resolve_model_type

logger = logging.getLogger("secureml.training")


def run_training_job(job_id: str, dataset_dir: str, config: dict[str, Any]) -> None:
    progress_tracker.update_job(job_id, status="running")
    progress_tracker.append_log(job_id, "Training job started.")

    device = get_device()
    model_type = resolve_model_type(config["model_type"])
    epochs = int(config["epochs"])
    batch_size = int(config["batch_size"])
    learning_rate = float(config["learning_rate"])
    freeze_backbone = bool(config["freeze_backbone"])

    try:
        train_dataset, val_dataset, class_names = load_datasets(
            dataset_dir=Path(dataset_dir),
            image_size=SUPPORTED_MODELS[model_type]["image_size"],
            seed=int(config.get("seed", 42)),
        )
        train_loader, val_loader = build_dataloaders(train_dataset, val_dataset, batch_size)

        model = build_model(model_type, len(class_names), freeze_backbone=freeze_backbone)
        model.to(device)

        criterion = nn.CrossEntropyLoss()
        optimizer = Adam(filter(lambda p: p.requires_grad, model.parameters()), lr=learning_rate)

        start_time = time.perf_counter()
        epoch_durations: list[float] = []
        for epoch in range(1, epochs + 1):
            model.train()
            running_loss = 0.0
            train_correct = 0
            train_total = 0
            epoch_start = time.perf_counter()

            for images, labels in train_loader:
                images = images.to(device)
                labels = labels.to(device)

                optimizer.zero_grad()
                outputs = model(images)
                loss = criterion(outputs, labels)
                loss.backward()
                optimizer.step()

                running_loss += loss.item() * images.size(0)
                _, preds = torch.max(outputs, 1)
                train_correct += (preds == labels).sum().item()
                train_total += labels.size(0)

            avg_train_loss = running_loss / len(train_loader.dataset)
            train_accuracy = train_correct / train_total if train_total else 0.0

            model.eval()
            correct = 0
            total = 0
            val_running_loss = 0.0
            all_preds: list[int] = []
            all_labels: list[int] = []
            with torch.no_grad():
                for images, labels in val_loader:
                    images = images.to(device)
                    labels = labels.to(device)
                    outputs = model(images)
                    loss = criterion(outputs, labels)
                    val_running_loss += loss.item() * images.size(0)
                    _, preds = torch.max(outputs, 1)
                    correct += (preds == labels).sum().item()
                    total += labels.size(0)
                    all_preds.extend(preds.cpu().tolist())
                    all_labels.extend(labels.cpu().tolist())

            val_accuracy = correct / total if total else 0.0
            avg_val_loss = val_running_loss / len(val_loader.dataset) if len(val_loader.dataset) else 0.0

            num_classes = len(class_names)
            confusion = [[0 for _ in range(num_classes)] for _ in range(num_classes)]
            for true_label, pred_label in zip(all_labels, all_preds):
                if 0 <= true_label < num_classes and 0 <= pred_label < num_classes:
                    confusion[true_label][pred_label] += 1

            per_class_accuracy = {}
            precision_scores = []
            recall_scores = []
            f1_scores = []
            for idx in range(num_classes):
                tp = confusion[idx][idx]
                fn = sum(confusion[idx][j] for j in range(num_classes)) - tp
                fp = sum(confusion[i][idx] for i in range(num_classes)) - tp
                denom_precision = tp + fp
                denom_recall = tp + fn
                precision = tp / denom_precision if denom_precision else 0.0
                recall = tp / denom_recall if denom_recall else 0.0
                f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
                precision_scores.append(precision)
                recall_scores.append(recall)
                f1_scores.append(f1)
                per_class_accuracy[class_names[idx]] = tp / (tp + fn) if (tp + fn) else 0.0

            macro_precision = sum(precision_scores) / num_classes if num_classes else 0.0
            macro_recall = sum(recall_scores) / num_classes if num_classes else 0.0
            macro_f1 = sum(f1_scores) / num_classes if num_classes else 0.0
            epoch_duration = time.perf_counter() - epoch_start
            epoch_durations.append(epoch_duration)

            progress_tracker.append_metrics(
                job_id,
                {
                    "train_loss": avg_train_loss,
                    "val_loss": avg_val_loss,
                    "train_accuracy": train_accuracy,
                    "val_accuracy": val_accuracy,
                    "precision": macro_precision,
                    "recall": macro_recall,
                    "f1": macro_f1,
                    "epoch_durations": epoch_duration,
                    "confusion_matrix": confusion,
                    "per_class_accuracy": per_class_accuracy,
                    "class_names": class_names,
                },
            )
            progress_tracker.update_job(
                job_id,
                current_epoch=epoch,
                progress=round(epoch / epochs * 100, 2),
            )
            progress_tracker.append_log(
                job_id,
                (
                    f"Epoch {epoch}/{epochs} - train_loss={avg_train_loss:.4f} "
                    f"val_loss={avg_val_loss:.4f} train_acc={train_accuracy:.4f} "
                    f"val_acc={val_accuracy:.4f}"
                ),
            )

        job_snapshot = progress_tracker.get_job(job_id) or {}
        metrics = job_snapshot.get("metrics", {})
        metrics["final_val_accuracy"] = val_accuracy
        metrics["final_train_loss"] = avg_train_loss
        metrics["final_val_loss"] = avg_val_loss
        metrics["final_train_accuracy"] = train_accuracy
        metrics["final_precision"] = macro_precision
        metrics["final_recall"] = macro_recall
        metrics["final_f1"] = macro_f1
        metrics["total_duration_sec"] = time.perf_counter() - start_time

        model_metadata = export_model(
            model=model,
            model_type=model_type,
            class_names=class_names,
            image_size=SUPPORTED_MODELS[model_type]["image_size"],
            metrics=metrics,
        )

        progress_tracker.update_job(
            job_id,
            status="completed",
            model_id=model_metadata["model_id"],
            progress=100.0,
        )
        progress_tracker.append_log(job_id, "Training completed successfully.")

    except Exception as exc:
        logger.exception("Training job failed: %s", exc)
        progress_tracker.update_job(job_id, status="failed", error=str(exc))
        progress_tracker.append_log(job_id, f"Training failed: {exc}")
