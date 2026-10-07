# vision/ — edge computer-vision package (camera -> YOLO -> seats -> telemetry).
# Importing this package must stay light: heavy imports (cv2, ultralytics) happen
# inside the modules that need them so backend code can reuse density/ground_truth.
