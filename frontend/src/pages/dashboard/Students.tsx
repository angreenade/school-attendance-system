import { useEffect, useRef, useState } from "react";
import { api } from "../../api/client";
import type { StudentOut } from "../../api/types";

const emptyForm = {
  student_id: "",
  first_name: "",
  last_name: "",
  grade: "",
  homeroom: "",
  guardian_name: "",
  consent_given: false,
};

export default function Students() {
  const [students, setStudents] = useState<StudentOut[]>([]);
  const [query, setQuery] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [enrollingFor, setEnrollingFor] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function load() {
    const res = await api.get("/api/students", { params: query ? { q: query } : {} });
    setStudents(res.data);
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query]);

  async function createStudent(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.post("/api/students", form);
      setForm(emptyForm);
      setShowForm(false);
      load();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Could not create student");
    }
  }

  async function deleteStudent(id: number) {
    if (!confirm("Permanently delete this student, including their face data and attendance history?")) return;
    await api.delete(`/api/students/${id}`);
    load();
  }

  function startEnroll(id: number) {
    setEnrollingFor(id);
    setTimeout(() => fileInputRef.current?.click(), 0);
  }

  async function onFileSelected(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || enrollingFor === null) return;
    setError(null);
    const data = new FormData();
    data.append("file", file);
    try {
      await api.post(`/api/students/${enrollingFor}/enroll-photo`, data, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      load();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Could not enroll photo");
    } finally {
      setEnrollingFor(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Students</h1>
        <button onClick={() => setShowForm((v) => !v)}>{showForm ? "Cancel" : "Add student"}</button>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {showForm && (
        <form className="inline-form" onSubmit={createStudent}>
          <input placeholder="School ID (e.g. STU1042)" required value={form.student_id}
            onChange={(e) => setForm({ ...form, student_id: e.target.value })} />
          <input placeholder="First name" required value={form.first_name}
            onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
          <input placeholder="Last name" required value={form.last_name}
            onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
          <input placeholder="Grade" value={form.grade}
            onChange={(e) => setForm({ ...form, grade: e.target.value })} />
          <input placeholder="Homeroom" value={form.homeroom}
            onChange={(e) => setForm({ ...form, homeroom: e.target.value })} />
          <input placeholder="Guardian name" value={form.guardian_name}
            onChange={(e) => setForm({ ...form, guardian_name: e.target.value })} />
          <label className="checkbox-label">
            <input type="checkbox" checked={form.consent_given}
              onChange={(e) => setForm({ ...form, consent_given: e.target.checked })} />
            Guardian consent for biometric (face) data collection on file
          </label>
          <button type="submit">Save student</button>
        </form>
      )}

      <input className="search-box" placeholder="Search by name or ID..." value={query} onChange={(e) => setQuery(e.target.value)} />

      <input type="file" accept="image/*" ref={fileInputRef} style={{ display: "none" }} onChange={onFileSelected} />

      <div className="table-card">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>School ID</th>
              <th>Grade</th>
              <th>Homeroom</th>
              <th>Consent</th>
              <th>Face enrolled</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {students.map((s) => (
              <tr key={s.id}>
                <td>{s.first_name} {s.last_name}</td>
                <td>{s.student_id}</td>
                <td>{s.grade ?? "–"}</td>
                <td>{s.homeroom ?? "–"}</td>
                <td>
                  <span className={`status-pill ${s.consent_given ? "status-pill-good" : "status-pill-critical"}`}>
                    {s.consent_given ? "On file" : "Missing"}
                  </span>
                </td>
                <td>
                  <span className={`status-pill ${s.is_enrolled_for_recognition ? "status-pill-good" : "status-pill-neutral"}`}>
                    {s.is_enrolled_for_recognition ? "Enrolled" : "Not enrolled"}
                  </span>
                </td>
                <td className="actions-cell">
                  <button className="link-btn" disabled={!s.consent_given} title={!s.consent_given ? "Requires consent on file" : ""} onClick={() => startEnroll(s.id)}>
                    Enroll face
                  </button>
                  <button className="link-btn danger" onClick={() => deleteStudent(s.id)}>Delete</button>
                </td>
              </tr>
            ))}
            {students.length === 0 && (
              <tr><td colSpan={7} className="muted">No students found.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
