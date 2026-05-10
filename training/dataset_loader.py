from __future__ import annotations

from pathlib import Path
from typing import Tuple

import torch
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, transforms

from training.config import DEFAULT_RANDOM_SEED, DEFAULT_VALIDATION_SPLIT


def build_transforms(image_size: int) -> transforms.Compose:
    return transforms.Compose(
        [
            transforms.Resize((image_size, image_size)),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
        ]
    )


def build_eval_transforms(image_size: int) -> transforms.Compose:
    return transforms.Compose(
        [
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
        ]
    )


def load_datasets(dataset_dir: Path, image_size: int, seed: int = DEFAULT_RANDOM_SEED) -> Tuple[torch.utils.data.Dataset, torch.utils.data.Dataset, list[str]]:
    train_transform = build_transforms(image_size)
    dataset = datasets.ImageFolder(str(dataset_dir), transform=train_transform)

    val_size = int(len(dataset) * DEFAULT_VALIDATION_SPLIT)
    if val_size == 0 and len(dataset) > 1:
        val_size = 1
    train_size = len(dataset) - val_size
    generator = torch.Generator().manual_seed(seed)

    train_dataset, val_dataset = random_split(dataset, [train_size, val_size], generator=generator)
    val_dataset.dataset.transform = build_eval_transforms(image_size)

    return train_dataset, val_dataset, dataset.classes


def build_dataloaders(
    train_dataset: torch.utils.data.Dataset,
    val_dataset: torch.utils.data.Dataset,
    batch_size: int,
) -> Tuple[DataLoader, DataLoader]:
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    return train_loader, val_loader
