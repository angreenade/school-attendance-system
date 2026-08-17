import { useEffect, useState } from "react";
import { api } from "../../api/client";
import type { ClassSectionOut, LocationOut, StudentOut } from "../../api/types";

const emptyForm = {
  name: "",
  term: "Winter Term",
  teacher_name: "",
  location_id: "",
  scheduled_start: "08:00",
  scheduled_days: "Mon,Tue,Wed,Thu,Fri",
};

export default function Classes() {
  const [classes, setClasses] = useState<ClassSectionOut[]>([]);
  const [locations, setLocations] = useState<LocationOut[]>([]);
  const [students, setStudents] = useState<StudentOut[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [showForm, setShowForm] = useState(false);
  const [enrollClassId, setEnrollClassId] = useState<number | null>(null);
  const [enrollStudentId, setEnrollStudentId] = useState("");

  function locationName(id: number | null) {
    return locations.find((l) => l.id === id)?.name ?? "–";
  }

  async function load() {
    const [c, l, s] = await Promise.all([
      api.get("/api/classes"),
      api.get("/api/locations"),
      api.get("/api/students"),
    ]);
    setClasses(c.data);
    setLocations(l.data);
    setStudents(s.data);
  }

  useEffect(() => {
    load();
  }, []);

  async function createClass(e: React.FormEvent) {
    e.preventDefault();
    await api.post("/api/classes", { ...form, location_id: form.location_id ? Number(form.location_id) : null });
    setForm(emptyForm);
    setShowForm(false);
    load();
  }

  async function deleteClass(id: number) {
    if (!confirm("Delete this class section?")) return;
    await api.delete(`/api/classes/${id}`);
    load();
  }

  async function enrollStudent() {
    if (!enrollClassId || !enrollStudentId) return;
    await api.post(`/api/classes/${enrollClassId}/enroll/${enrollStudentId}`);
    setEnrollStudentId("");
    setEnrollClassId(null);
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Classes</h1>
        <button onClick={() => setShowForm((v) => !v)}>{showForm ? "Cancel" : "Add class"}</button>
      </div>

      {showForm && (
        <form className="inline-form" onSubmit={createClass}>
          <input placeholder="Class name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <input placeholder="Term" value={form.term} onChange={(e) => setForm({ ...form, term: e.target.value })} />
          <input placeholder="Teacher" value={form.teacher_name} onChange={(e) => setForm({ ...form, teacher_name: e.target.value })} />
          <select value={form.location_id} onChange={(e) => setForm({ ...form, location_id: e.target.value })}>
            <option value="">No default location</option>
            {locations.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
          </select>
          <input type="time" value={form.scheduled_start} onChange={(e) => setForm({ ...form, scheduled_start: e.target.value })} />
          <input placeholder="Days (Mon,Tue,...)" value={form.scheduled_days} onChange={(e) => setForm({ ...form, scheduled_days: e.target.value })} />
          <button type="submit">Save class</button>
        </form>
      )}

      <div className="table-card">
        <table>
          <thead>
            <tr>
              <th>Class</th>
              <th>Term</th>
              <th>Teacher</th>
              <th>Location</th>
              <th>Schedule</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {classes.map((c) => (
              <tr key={c.id}>
                <td>{c.name}</td>
                <td>{c.term}</td>
                <td>{c.teacher_name ?? "–"}</td>
                <td>{locationName(c.location_id)}</td>
                <td>{c.scheduled_start} &middot; {c.scheduled_days}</td>
                <td className="actions-cell">
                  <button className="link-btn" onClick={() => setEnrollClassId(c.id)}>Enroll student</button>
                  <button className="link-btn danger" onClick={() => deleteClass(c.id)}>Delete</button>
                </td>
              </tr>
            ))}
            {classes.length === 0 && <tr><td colSpan={6} className="muted">No classes yet.</td></tr>}
          </tbody>
        </table>
      </div>

      {enrollClassId !== null && (
        <div className="modal-backdrop" onClick={() => setEnrollClassId(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Enroll a student</h3>
            <select value={enrollStudentId} onChange={(e) => setEnrollStudentId(e.target.value)}>
              <option value="">Select a student...</option>
              {students.map((s) => <option key={s.id} value={s.id}>{s.first_name} {s.last_name} ({s.student_id})</option>)}
            </select>
            <div className="modal-actions">
              <button className="link-btn" onClick={() => setEnrollClassId(null)}>Cancel</button>
              <button onClick={enrollStudent}>Enroll</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
