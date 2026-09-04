from ultralytics import YOLO

# TEST-ONLY reconstruction scaffold.
# This creates a new experiment; it does not reproduce the historical checkpoint.
model = YOLO("models/yolov8n_pretrained_coco_baseline.pt")
model.train(
    data="synthetic_test_dataset/custom_data_TEST_ONLY.yaml",
    epochs=25,
    imgsz=640,
    batch=16,
    device=0,
)
