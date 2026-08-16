#!/usr/bin/env bash
# Downloads the two OpenCV ONNX models the face engine needs. The face
# recognition model is ~37MB, too large to ship inside the project zip, so
# it's fetched here instead. Safe to re-run.
set -e
cd "$(dirname "$0")/app/ml_models"

fetch() {
  local name="$1" url="$2"
  if [ -f "$name" ]; then
    echo "Already have $name, skipping."
    return
  fi
  echo "Downloading $name ..."
  curl -sL -A "Mozilla/5.0" -o "$name" "$url"
  echo "  -> $(du -h "$name" | cut -f1)"
}

fetch "face_detection_yunet_2023mar.onnx" \
  "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"

fetch "face_recognition_sface_2021dec.onnx" \
  "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"

echo "Done. Both model files are in app/ml_models/."
