# VisionGuard AI: Custom YOLO11 Dataset Training Guide

This guide details how to annotate, organize, and train a custom **YOLOv11** object detection model for conveyor belt defect inspection.

> **Important Note**: General-purpose pretrained vision models (such as standard COCO pretrained models) only recognize standard objects like cars, dogs, and chairs. They **cannot** detect domain-specific conveyor belt anomalies (such as longitudinal tears, surface cracks, belt tracking misalignments, roller faults, or spillage) unless fine-tuned on an annotated industrial dataset containing these target defect classes.

---

## 1. Supported Defect Classes

Your dataset annotations should conform to these 5 target defect categories:
1. `Cracks`: Surface micro/macro cracks on rubber belt.
2. `Tears`: Longitudinal rips or tears caused by sharp debris.
3. `Misalignment`: Tracking drift where belt wanders off center.
4. `Roller faults`: Worn out, seized, or missing rollers.
5. `Material spillage`: Accumulated ore, dust, or coal overflow.

---

## 2. Recommended Dataset Directory Structure

Organize your dataset in standard YOLO format:

```text
dataset/
├── images/
│   ├── train/
│   │   ├── frame_001.jpg
│   │   └── frame_002.jpg
│   ├── val/
│   │   ├── frame_101.jpg
│   │   └── frame_102.jpg
│   └── test/
│       └── frame_201.jpg
└── labels/
    ├── train/
    │   ├── frame_001.txt
    │   └── frame_002.txt
    ├── val/
    │   ├── frame_101.txt
    │   └── frame_102.txt
    └── test/
        └── frame_201.txt
```

Each label text file contains lines in YOLO bounding box format:
`<class_id> <x_center> <y_center> <width> <height>` (normalized 0.0 - 1.0).

---

## 3. Creating `data.yaml`

Copy `docs/data.yaml.example` to `docs/data.yaml` and configure paths:

```yaml
path: ./dataset
train: images/train
val: images/val
test: images/test

names:
  0: Cracks
  1: Tears
  2: Misalignment
  3: Roller faults
  4: Material spillage
```

---

## 4. Running the Training Script

Run the automated training script included in VisionGuard AI:

```bash
python train_yolo.py --data docs/data.yaml --model yolo11n.pt --epochs 50 --imgsz 640 --batch 16
```

### Command Options:
- `--data`: Path to `data.yaml`.
- `--model`: Base weights (`yolo11n.pt`, `yolo11s.pt`, `yolo11m.pt`).
- `--epochs`: Number of passes over dataset (recommended 50 - 100).
- `--export-path`: Destination path (`models/best.pt`).

---

## 5. Evaluation & Validation

During training and validation, inspect the output metrics:
- **Precision (P)**: Accuracy of positive predictions.
- **Recall (R)**: Coverage of true defect instances.
- **mAP50**: Mean Average Precision at IoU threshold 0.50.
- **mAP50-95**: Mean Average Precision averaged across IoU 0.50 to 0.95.
- **Inference Time (ms)**: Latency per image.

---

## 6. Saving Model Weights to `models/best.pt`

The `train_yolo.py` script automatically copies the best performing checkpoint to `models/best.pt`.
You can also copy it manually:

```bash
cp runs/detect/visionguard_conveyor_yolo11/weights/best.pt models/best.pt
```

Once `models/best.pt` is present, restart or refresh VisionGuard AI to begin real-time defect detections.
