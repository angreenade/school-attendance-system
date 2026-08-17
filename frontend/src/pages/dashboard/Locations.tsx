import { useEffect, useState } from "react";
import { api } from "../../api/client";
import type { LocationOut } from "../../api/types";

export default function Locations() {
  const [locations, setLocations] = useState<LocationOut[]>([]);
  const [name, setName] = useState("");
  const [type, setType] = useState("classroom");

  async function load() {
    const res = await api.get("/api/locations");
    setLocations(res.data);
  }

  useEffect(() => {
    load();
  }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    await api.post("/api/locations", { name, location_type: type });
    setName("");
    load();
  }

  async function remove(id: number) {
    if (!confirm("Delete this location? Its kiosk will stop working.")) return;
    await api.delete(`/api/locations/${id}`);
    load();
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Locations / Kiosks</h1>
      </div>
      <p className="muted">
        Each location gets a unique kiosk key. Open <code>/kiosk</code> on the device placed at that
        door/entrance and select the matching location to activate scanning there.
      </p>

      <form className="inline-form" onSubmit={create}>
        <input placeholder="Location name (e.g. Room 305)" required value={name} onChange={(e) => setName(e.target.value)} />
        <select value={type} onChange={(e) => setType(e.target.value)}>
          <option value="classroom">Classroom</option>
          <option value="study_room">Study room</option>
          <option value="entrance">Entrance</option>
        </select>
        <button type="submit">Add location</button>
      </form>

      <div className="table-card">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Kiosk key</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {locations.map((l) => (
              <tr key={l.id}>
                <td>{l.name}</td>
                <td>{l.location_type.replace("_", " ")}</td>
                <td><code>{l.kiosk_key}</code></td>
                <td>
                  <button className="link-btn danger" onClick={() => remove(l.id)}>Delete</button>
                </td>
              </tr>
            ))}
            {locations.length === 0 && <tr><td colSpan={4} className="muted">No locations yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
