# Model Weights Directory

Place custom trained YOLOv11 model weights file named `best.pt` in this directory:
`models/best.pt`

To train custom weights on conveyor belt defect datasets:
```powershell
python train_yolo.py --data docs/data.yaml --model yolo11n.pt --epochs 50 --imgsz 640 --batch 16
```
