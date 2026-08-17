import { useCallback, useEffect, useRef, useState } from "react";
import * as faceapi from "face-api.js";
import { api } from "../api/client";
import type { LocationOut, ScanResult } from "../api/types";

const MODEL_URL = "/models";
const DETECT_INTERVAL_MS = 250;
// How long a face must be continuously tracked before we submit it to the
// server for identification -- avoids sending blurry in-motion frames.
const STABLE_MS_BEFORE_SUBMIT = 700;
// Minimum gap between submissions so we don't hammer the backend while a
// student lingers in frame (server also dedupes by student+location).
const SUBMIT_COOLDOWN_MS = 4000;

type KioskLocation = { name: string; kiosk_key: string };

export default function Kiosk() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const captureCanvasRef = useRef<HTMLCanvasElement>(document.createElement("canvas"));

  const [modelsReady, setModelsReady] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [location, setLocation] = useState<KioskLocation | null>(() => {
    const stored = localStorage.getItem("kiosk_location");
    return stored ? JSON.parse(stored) : null;
  });
  const [availableLocations, setAvailableLocations] = useState<LocationOut[]>([]);
  const [feedback, setFeedback] = useState<ScanResult | null>(null);
  const [faceBox, setFaceBox] = useState<{ x: number; y: number; w: number; h: number } | null>(null);

  const stableSinceRef = useRef<number | null>(null);
  const lastSubmitRef = useRef<number>(0);
  const submittingRef = useRef(false);

  // ---- Load face-api models once ----
  useEffect(() => {
    faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL).then(() => setModelsReady(true));
  }, []);

  // ---- Fetch locations if this kiosk hasn't been configured yet ----
  useEffect(() => {
    if (!location) {
      api.get("/api/locations/public").then((res) => setAvailableLocations(res.data)).catch(() => {});
    }
  }, [location]);

  // ---- Start camera ----
  useEffect(() => {
    if (!location) return;
    let stream: MediaStream | null = null;
    navigator.mediaDevices
      .getUserMedia({ video: { width: 640, height: 480 }, audio: false })
      .then((s) => {
        stream = s;
        if (videoRef.current) {
          videoRef.current.srcObject = s;
        }
      })
      .catch(() => setCameraError("Could not access the camera. Please grant camera permission and reload."));
    return () => {
      stream?.getTracks().forEach((t) => t.stop());
    };
  }, [location]);

  const submitScan = useCallback(async () => {
    if (!location || submittingRef.current) return;
    submittingRef.current = true;
    try {
      const video = videoRef.current!;
      const canvas = captureCanvasRef.current;
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d")!;
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      const image_base64 = canvas.toDataURL("image/jpeg", 0.85);

      const res = await api.post<ScanResult>("/api/attendance/scan", {
        location_kiosk_key: location.kiosk_key,
        image_base64,
      });
      setFeedback(res.data);
      lastSubmitRef.current = Date.now();
      setTimeout(() => setFeedback(null), 3800);
    } catch {
      setFeedback({ matched: false, message: "Connection error -- could not reach the server", duplicate: false });
      setTimeout(() => setFeedback(null), 3000);
    } finally {
      submittingRef.current = false;
    }
  }, [location]);

  // ---- Live tracking loop ----
  useEffect(() => {
    if (!modelsReady || !location) return;
    let cancelled = false;

    const interval = setInterval(async () => {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (!video || !canvas || video.readyState !== 4) return;

      const detection = await faceapi.detectSingleFace(video, new faceapi.TinyFaceDetectorOptions({ inputSize: 224 }));
      if (cancelled) return;

      const displaySize = { width: video.clientWidth, height: video.clientHeight };
      canvas.width = displaySize.width;
      canvas.height = displaySize.height;
      const ctx = canvas.getContext("2d")!;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      if (detection) {
        const resized = faceapi.resizeResults(detection, displaySize);
        const { x, y, width, height } = resized.box;
        setFaceBox({ x, y, w: width, h: height });

        if (stableSinceRef.current === null) stableSinceRef.current = Date.now();
        const stableFor = Date.now() - stableSinceRef.current;
        const cooldownOk = Date.now() - lastSubmitRef.current > SUBMIT_COOLDOWN_MS;

        if (stableFor > STABLE_MS_BEFORE_SUBMIT && cooldownOk && !feedback) {
          submitScan();
        }
      } else {
        stableSinceRef.current = null;
        setFaceBox(null);
      }
    }, DETECT_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [modelsReady, location, feedback, submitScan]);

  function chooseLocation(loc: LocationOut) {
    const value = { name: loc.name, kiosk_key: loc.kiosk_key };
    localStorage.setItem("kiosk_location", JSON.stringify(value));
    setLocation(value);
  }

  function changeLocation() {
    localStorage.removeItem("kiosk_location");
    setLocation(null);
  }

  if (!location) {
    return (
      <div className="kiosk-setup">
        <h1>Configure This Kiosk</h1>
        <p className="muted">Select which classroom or entrance this scanning station is placed at.</p>
        <div className="location-grid">
          {availableLocations.map((loc) => (
            <button key={loc.id} className="location-choice" onClick={() => chooseLocation(loc)}>
              <strong>{loc.name}</strong>
              <span className="muted">{loc.location_type.replace("_", " ")}</span>
            </button>
          ))}
        </div>
        {availableLocations.length === 0 && <p className="muted">No locations found. Ask an admin to create one in the dashboard.</p>}
      </div>
    );
  }

  return (
    <div className="kiosk-screen">
      <div className="kiosk-header">
        <div>
          <h1>{location.name}</h1>
          <p className="muted">Face-scan attendance &middot; look at the camera</p>
        </div>
        <button className="link-btn" onClick={changeLocation}>Change location</button>
      </div>

      <div className="camera-wrap">
        <video ref={videoRef} autoPlay muted playsInline className="camera-video" />
        <canvas ref={canvasRef} className="camera-overlay" />
        {faceBox && (
          <div
            className="face-box"
            style={{ left: faceBox.x, top: faceBox.y, width: faceBox.w, height: faceBox.h }}
          />
        )}

        {cameraError && <div className="camera-error">{cameraError}</div>}
        {!modelsReady && !cameraError && <div className="camera-loading">Loading face tracking...</div>}

        {feedback && (
          <div className={`scan-feedback ${feedback.matched ? (feedback.duplicate ? "info" : "success") : "warn"}`}>
            {feedback.matched ? (
              <>
                <div className="scan-feedback-icon">{feedback.duplicate ? "✓" : "✓"}</div>
                <div className="scan-feedback-name">{feedback.student_name}</div>
                <div className="scan-feedback-meta">
                  {feedback.status === "late" ? "Marked LATE" : "Marked on time"} &middot;{" "}
                  {feedback.timestamp && new Date(feedback.timestamp).toLocaleTimeString()}
                </div>
                {feedback.duplicate && <div className="scan-feedback-meta">(already recorded recently)</div>}
              </>
            ) : (
              <>
                <div className="scan-feedback-icon">!</div>
                <div className="scan-feedback-name">{feedback.message}</div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
