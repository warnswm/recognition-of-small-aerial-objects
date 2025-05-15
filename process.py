import os
import numpy as np
import cv2
import torch
from PIL import Image
import pathlib
from roboflow import Roboflow
import tempfile

from ultralytics import YOLO


my_model = YOLO('C:\\Users\\warn\\Downloads\\40Epoch.pt')

model_aerial = YOLO("yolo11x-obb.pt")

def process_frame(frame, mode="normal"):
    if mode == "aerial":
        results = model_aerial(frame)

        for result in results:
            # result.obb.xyxyxyxy – список координат для каждого бокса
            # result.obb.cls.int() – индексы классов, result.names – имена классов
            # result.obb.conf – значения confidence для каждого бокса
            for box, cls, conf in zip(result.obb.xyxyxyxy,
                                      result.obb.cls.int().tolist(),
                                      result.obb.conf):

                class_name = result.names[cls]
                pts = np.array(box).reshape((-1, 1, 2)).astype(np.int32)
                cv2.polylines(frame, [pts], isClosed=True, color=(0, 0, 255), thickness=2)
                x, y = pts[0][0]
                cv2.putText(frame, f"{class_name}: {conf * 100:.2f}%", (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        return frame
    else:
        results = my_model(frame)

        for result in results:
            boxes = result.boxes
            for xyxy, cls_id, conf in zip(
                    boxes.xyxy,
                    boxes.cls.int().tolist(),
                    boxes.conf
            ):
                x1, y1, x2, y2 = map(int, xyxy)

                cv2.rectangle(frame, (x1, y1), (x2, y2),
                              color=(255, 0, 0), thickness=2) #ili red 0,0,255

                class_name = result.names[cls_id]
                label = f"{class_name}: {conf * 100:.2f}%"
                cv2.putText(frame, label,
                            (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5, (255, 0, 0), 2)

        return frame


def process_video(videoPath, mode="normal"):
    """
    Полностью обрабатывает видеофайл:
    - Считывает видео по кадрам.
    - Обрабатывает каждый кадр с помощью модели (режим 'normal' или 'aerial'),
      добавляя bounding box и процентное значение confidence.
    - Сохраняет обработанное видео в папке Downloads.

    :param videoPath: Путь к исходному видеофайлу.
    :param mode: Режим обработки ('normal' или 'aerial').
    :return: Путь к сохранённому обработанному видео.
    """
    cap = cv2.VideoCapture(videoPath)
    if not cap.isOpened():
        raise ValueError("Не удалось открыть видеофайл.")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    downloadsPath = os.path.join(os.path.expanduser("~"), "Downloads")
    baseName = os.path.basename(videoPath)
    outputFileName = os.path.join(downloadsPath, f"processed_{baseName}")

    fourcc = cv2.VideoWriter.fourcc(*'mp4v')
    out = cv2.VideoWriter(outputFileName, fourcc, fps, (width, height))

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if mode == "aerial":
            results = model_aerial(frame)
            for result in results:
                for box, cls, conf in zip(result.obb.xyxyxyxy, result.obb.cls.int().tolist(), result.obb.conf):
                    className = result.names[cls]
                    pts = np.array(box).reshape((-1, 1, 2)).astype(np.int32)
                    cv2.polylines(frame, [pts], isClosed=True, color=(0, 0, 255), thickness=2)
                    x, y = pts[0][0]
                    cv2.putText(frame, f"{className}: {conf * 100:.2f}%", (x, y - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        else:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tempFilename = tmp.name
                cv2.imwrite(tempFilename, frame)
            result = model_normal.predict(tempFilename, confidence=40).json()
            os.remove(tempFilename)
            for pred in result.get("predictions", []):
                centerX = pred["x"]
                centerY = pred["y"]
                widthBox = pred["width"]
                heightBox = pred["height"]
                className = pred["class"]
                conf = pred["confidence"]
                x1 = int(centerX - widthBox / 2)
                y1 = int(centerY - heightBox / 2)
                x2 = int(centerX + widthBox / 2)
                y2 = int(centerY + heightBox / 2)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                cv2.putText(frame, f"{className}: {conf * 100:.2f}%", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        out.write(frame)

    cap.release()
    out.release()
    return outputFileName