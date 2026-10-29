"""
VisionGuard AI - YOLOv11 Conveyor Belt Defect Model Trainer
Usage:
    python train_yolo.py --data docs/data.yaml --epochs 50 --imgsz 640 --batch 16
"""

import os
import sys
import argparse
import time
from pathlib import Path

def parse_args():
    parser = argparse.ArgumentParser(description="Train custom YOLOv11 model on conveyor belt defect dataset")
    parser.add_argument("--data", type=str, default="docs/data.yaml", help="Path to data.yaml dataset config file")
    parser.add_argument("--model", type=str, default="yolo11n.pt", help="Base pretrained YOLO11 model (e.g., yolo11n.pt, yolo11s.pt)")
    parser.add_argument("--epochs", type=int, default=50, help="Number of training epochs")
    parser.add_argument("--imgsz", type=int, default=640, help="Input image size (pixels)")
    parser.add_argument("--batch", type=int, default=16, help="Batch size")
    parser.add_argument("--export-path", type=str, default="models/best.pt", help="Target destination for trained weights")
    return parser.parse_args()

def main():
    args = parse_args()
    print("=" * 60)
    print(" VisionGuard AI - YOLOv11 Custom Model Training ")
    print("=" * 60)

    if not os.path.exists(args.data):
        print(f"[ERROR] Dataset configuration file '{args.data}' not found.")
        print("Please prepare your conveyor belt dataset and create a data.yaml file.")
        print("Refer to 'docs/training_guide.md' for directory structure and instructions.")
        sys.exit(1)

    try:
        from ultralytics import YOLO
    except ImportError:
        print("[ERROR] Ultralytics package is not installed. Install via: pip install ultralytics")
        sys.exit(1)

    print(f"[*] Loading base model: {args.model}")
    model = YOLO(args.model)

    print(f"[*] Starting training on dataset: {args.data}")
    print(f"[*] Parameters: epochs={args.epochs}, imgsz={args.imgsz}, batch={args.batch}")

    start_time = time.time()
    
    # Train the model
    results = model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        name="visionguard_conveyor_yolo11",
        exist_ok=True
    )

    elapsed_min = (time.time() - start_time) / 60.0
    print(f"\n[+] Training finished in {elapsed_min:.2f} minutes.")

    # Validate model and compute evaluation metrics
    print("\n[*] Running validation and calculating performance metrics (Precision, Recall, mAP50, mAP50-95)...")
    val_results = model.val()

    # Extract metrics if available
    try:
        metrics = val_results.results_dict
        print("\n--- Validation Performance Metrics ---")
        print(f"  Precision: {metrics.get('metrics/precision(B)', 0.0):.4f}")
        print(f"  Recall:    {metrics.get('metrics/recall(B)', 0.0):.4f}")
        print(f"  mAP50:     {metrics.get('metrics/mAP50(B)', 0.0):.4f}")
        print(f"  mAP50-95:  {metrics.get('metrics/mAP50-95(B)', 0.0):.4f}")
    except Exception as e:
        print(f"[*] Validation summary available in runs/detect/visionguard_conveyor_yolo11")

    # Locate best.pt
    best_weights = Path("runs/detect/visionguard_conveyor_yolo11/weights/best.pt")
    if best_weights.exists():
        target_dir = Path(args.export-path).parent
        target_dir.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy(best_weights, args.export_path)
        print(f"\n[SUCCESS] Trained model weights successfully copied to: {args.export_path}")
        print("VisionGuard AI backend will now automatically load these custom defect detection weights.")
    else:
        print(f"\n[WARNING] Could not locate trained weights at {best_weights}.")

if __name__ == "__main__":
    main()
