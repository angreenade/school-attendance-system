import { useEffect, useState } from "react";
import { api } from "../../api/client";
import type { AttendanceLogOut, LocationOut, StudentOut } from "../../api/types";

export default function Attendance() {
  const [logs, setLogs] = useState<AttendanceLogOut[]>([]);
  const [locations, setLocations] = useState<LocationOut[]>([]);
  const [students, setStudents] = useState<StudentOut[]>([]);

  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [studentId, setStudentId] = useState("");
  const [locationId, setLocationId] = useState("");
  const [status, setStatus] = useState("");

  useEffect(() => {
    api.get("/api/locations").then((res) => setLocations(res.data));
    api.get("/api/students").then((res) => setStudents(res.data));
  }, []);

  function buildParams() {
    const params: Record<string, string> = {};
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    if (studentId) params.student_id = studentId;
    if (locationId) params.location_id = locationId;
    if (status) params.status = status;
    return params;
  }

  async function runQuery() {
    const res = await api.get("/api/attendance", { params: buildParams() });
    setLogs(res.data);
  }

  useEffect(() => {
    runQuery();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function exportCsv() {
    const params = new URLSearchParams(buildParams());
    const token = localStorage.getItem("attendance_token") || "";
    fetch(`/api/attendance/export.csv?${params.toString()}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "attendance_export.csv";
        a.click();
        URL.revokeObjectURL(url);
      });
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Attendance Log</h1>
        <button onClick={exportCsv}>Export CSV</button>
      </div>

      <div className="filter-bar">
        <label>
          From
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
        </label>
        <label>
          To
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        </label>
        <label>
          Student
          <select value={studentId} onChange={(e) => setStudentId(e.target.value)}>
            <option value="">All students</option>
            {students.map((s) => (
              <option key={s.id} value={s.id}>{s.first_name} {s.last_name} ({s.student_id})</option>
            ))}
          </select>
        </label>
        <label>
          Location
          <select value={locationId} onChange={(e) => setLocationId(e.target.value)}>
            <option value="">All locations</option>
            {locations.map((l) => (
              <option key={l.id} value={l.id}>{l.name}</option>
            ))}
          </select>
        </label>
        <label>
          Status
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">Any status</option>
            <option value="on_time">On time</option>
            <option value="late">Late</option>
          </select>
        </label>
        <button onClick={runQuery}>Apply filters</button>
      </div>

      <div className="table-card">
        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Student</th>
              <th>School ID</th>
              <th>Location</th>
              <th>Class</th>
              <th>Status</th>
              <th>Confidence</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id}>
                <td>{new Date(log.timestamp).toLocaleString()}</td>
                <td>{log.student_name}</td>
                <td>{log.student_school_id}</td>
                <td>{log.location_name}</td>
                <td>{log.class_section_name ?? "–"}</td>
                <td>
                  <span className={`status-pill ${log.status === "late" ? "status-pill-warning" : "status-pill-good"}`}>
                    {log.status === "late" ? "Late" : "On time"}
                  </span>
                </td>
                <td>{log.match_confidence.toFixed(2)}</td>
              </tr>
            ))}
            {logs.length === 0 && (
              <tr><td colSpan={7} className="muted">No attendance records match these filters.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
