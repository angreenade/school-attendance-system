"""
Face detection + recognition engine.

Uses OpenCV's bundled DNN models (no heavyweight ML framework, no compiled
dlib needed):
  - YuNet (face_detection_yunet_2023mar.onnx): fast face detector that also
    returns 5-point landmarks, used both for locating a face and for
    aligning it before embedding.
  - SFace (face_recognition_sface_2021dec.onnx): produces a 128-d embedding
    per aligned face; identity is decided by cosine similarity between
    embeddings.

This mirrors what happens client-side in the kiosk (face-api.js runs a
lightweight detector in the browser purely for live tracking/box-drawing
UX) -- the server always re-detects and re-embeds the submitted frame
itself rather than trusting anything computed in the browser, since the
browser is not a trusted boundary for identity decisions.
"""
import base64
import re
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

from .config import settings


@dataclass
class DetectedFace:
    embedding: np.ndarray  # float32[128]
    box: tuple  # (x, y, w, h) in pixel coords of the source image
    detection_score: float


class FaceEngine:
    def __init__(self):
        detector_path = f"{settings.ml_models_dir}/face_detection_yunet_2023mar.onnx"
        recognizer_path = f"{settings.ml_models_dir}/face_recognition_sface_2021dec.onnx"

        # input_size is updated per-image at inference time via setInputSize.
        self.detector = cv2.FaceDetectorYN_create(
            detector_path, "", (320, 320), score_threshold=0.7, nms_threshold=0.3, top_k=5000
        )
        self.recognizer = cv2.FaceRecognizerSF_create(recognizer_path, "")

    def _detect_all(self, image_bgr: np.ndarray) -> np.ndarray:
        h, w = image_bgr.shape[:2]
        self.detector.setInputSize((w, h))
        _, faces = self.detector.detect(image_bgr)
        return faces if faces is not None else np.empty((0, 15))

    def largest_face_embedding(self, image_bgr: np.ndarray) -> Optional[DetectedFace]:
        """Detect faces in an image and return the embedding for the largest one
        (closest to the camera / most likely the person who just walked up)."""
        faces = self._detect_all(image_bgr)
        if len(faces) == 0:
            return None

        # Pick the face with the largest bounding-box area.
        areas = faces[:, 2] * faces[:, 3]
        best_idx = int(np.argmax(areas))
        face_row = faces[best_idx]

        aligned = self.recognizer.alignCrop(image_bgr, face_row)
        embedding = self.recognizer.feature(aligned).flatten().astype(np.float32)

        x, y, w, h = face_row[0:4].astype(int)
        score = float(face_row[-1])
        return DetectedFace(embedding=embedding, box=(int(x), int(y), int(w), int(h)), detection_score=score)

    def all_face_embeddings(self, image_bgr: np.ndarray) -> list[DetectedFace]:
        """Used during enrollment to make sure exactly one face is in the photo."""
        faces = self._detect_all(image_bgr)
        results = []
        for face_row in faces:
            aligned = self.recognizer.alignCrop(image_bgr, face_row)
            embedding = self.recognizer.feature(aligned).flatten().astype(np.float32)
            x, y, w, h = face_row[0:4].astype(int)
            results.append(
                DetectedFace(embedding=embedding, box=(int(x), int(y), int(w), int(h)), detection_score=float(face_row[-1]))
            )
        return results

    def cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        return float(self.recognizer.match(
            emb1.reshape(1, -1), emb2.reshape(1, -1), cv2.FaceRecognizerSF_FR_COSINE
        ))

    def find_best_match(self, probe: np.ndarray, candidates: list[tuple[int, np.ndarray]]):
        """candidates: list of (student_db_id, embedding). Returns (student_db_id, score) or (None, best_score)."""
        best_id, best_score = None, -1.0
        for student_id, emb in candidates:
            score = self.cosine_similarity(probe, emb)
            if score > best_score:
                best_score = score
                best_id = student_id
        if best_score >= settings.face_match_threshold:
            return best_id, best_score
        return None, best_score


def decode_base64_image(data: str) -> np.ndarray:
    """Accepts either a raw base64 string or a data: URL and returns a BGR numpy image."""
    if "," in data and data.strip().startswith("data:"):
        data = data.split(",", 1)[1]
    data = re.sub(r"\s", "", data)
    raw = base64.b64decode(data)
    arr = np.frombuffer(raw, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Could not decode image data")
    return image


def embedding_to_bytes(embedding: np.ndarray) -> bytes:
    return embedding.astype(np.float32).tobytes()


def bytes_to_embedding(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)


# Singleton instance shared across requests (model loading is not free).
face_engine = FaceEngine()
