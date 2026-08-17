import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

export default function DashboardLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div className="dash-shell">
      <aside className="dash-sidebar">
        <div className="dash-brand">School Attendance</div>
        <nav>
          <NavLink to="/dashboard" end>Overview</NavLink>
          <NavLink to="/dashboard/attendance">Attendance Log</NavLink>
          <NavLink to="/dashboard/students">Students</NavLink>
          <NavLink to="/dashboard/classes">Classes</NavLink>
          <NavLink to="/dashboard/locations">Locations / Kiosks</NavLink>
        </nav>
        <div className="dash-user">
          <div>
            <strong>{user?.full_name}</strong>
            <span className="muted">{user?.role}</span>
          </div>
          <button className="link-btn" onClick={handleLogout}>Sign out</button>
        </div>
      </aside>
      <main className="dash-main">
        <Outlet />
      </main>
    </div>
  );
}
