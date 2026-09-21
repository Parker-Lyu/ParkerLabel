#!/usr/bin/env python3
import re

import cv2
import numpy as np


def build_value(label, information):
    match = re.search(rf"^\s*{re.escape(label)}:\s*(.+)$", information, re.MULTILINE)
    if not match:
        raise RuntimeError(f"Missing OpenCV build field: {label}")
    return match.group(1).strip()


def optional_build_value(label, information):
    match = re.search(rf"^\s*{re.escape(label)}:\s*(.+)$", information, re.MULTILINE)
    return match.group(1).strip() if match else None


def main():
    information = cv2.getBuildInformation()
    modules = set(build_value("To be built", information).split())
    expected = {"core", "flann", "geometry", "imgcodecs", "imgproc", "python3"}
    if modules != expected:
        raise RuntimeError(f"Unexpected OpenCV modules: {sorted(modules)}")
    forbidden = {"dnn", "highgui", "objdetect", "text", "video", "videoio"}
    if modules & forbidden:
        raise RuntimeError(f"Forbidden OpenCV modules: {sorted(modules & forbidden)}")
    for label in ("FFMPEG", "GStreamer", "OpenEXR"):
        value = optional_build_value(label, information)
        if value not in (None, "NO"):
            raise RuntimeError(f"{label} must be disabled, got {value}")

    source = np.zeros((24, 32, 3), dtype=np.uint8)
    source[4:20, 8:24] = (10, 120, 240)
    ok, encoded = cv2.imencode(".png", source)
    decoded = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if not ok or decoded is None or not np.array_equal(source, decoded):
        raise RuntimeError("PNG encode/decode failed")
    ok, encoded = cv2.imencode(".jpg", source)
    if not ok or cv2.imdecode(encoded, cv2.IMREAD_COLOR) is None:
        raise RuntimeError("JPEG encode/decode failed")

    rgb = cv2.cvtColor(decoded, cv2.COLOR_BGR2RGB)
    resized = cv2.resize(rgb, (16, 12), interpolation=cv2.INTER_AREA)
    binary = (resized[:, :, 0] > 0).astype(np.uint8)
    cv2.connectedComponentsWithStats(binary, connectivity=8)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    cv2.dilate(binary, kernel, iterations=1)
    cv2.erode(binary, kernel, iterations=1)
    canvas = np.zeros_like(source)
    cv2.line(canvas, (0, 0), (31, 23), (255, 255, 255), 2, cv2.LINE_8)
    cv2.circle(canvas, (16, 12), 4, (255, 255, 255), -1)
    cv2.addWeighted(source, 0.5, canvas, 0.5, 0)
    print(f"OpenCV {cv2.__version__}: {', '.join(sorted(modules))}")


if __name__ == "__main__":
    main()
