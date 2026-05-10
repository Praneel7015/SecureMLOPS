# Dataset ZIP Example

Use the following folder layout when creating `dataset.zip` for the Training tab:

```
dataset.zip
└── dataset/
    ├── cat/
    │   ├── cat_001.jpg
    │   └── cat_002.jpg
    ├── dog/
    │   ├── dog_001.jpg
    │   └── dog_002.jpg
    └── classes.json
```

`classes.json` must list each class folder name:

```json
{
  "classes": ["cat", "dog"]
}
```

Supported image formats: `.jpg`, `.jpeg`, `.png`.
