import axios from "axios";

// In dev, Vite proxies /api to the FastAPI backend (see vite.config.ts).
// In a real deployment, set VITE_API_BASE_URL to the backend's public URL.
const baseURL = import.meta.env.VITE_API_BASE_URL || "";

export const api = axios.create({ baseURL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("attendance_token");
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err?.response?.status === 401) {
      localStorage.removeItem("attendance_token");
      localStorage.removeItem("attendance_user");
      if (!window.location.pathname.startsWith("/login") && !window.location.pathname.startsWith("/kiosk")) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(err);
  }
);
