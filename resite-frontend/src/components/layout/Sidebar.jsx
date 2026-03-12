import { NavLink, useNavigate } from "react-router-dom";

function Sidebar() {
  const navigate = useNavigate();

  function handleLogout() {
    localStorage.removeItem("auth");
    navigate("/login");
  }

  return (
    <aside className="sidebar">
      <div className="sidebar__logo">🧑</div>

      <nav className="sidebar__nav">
        <NavLink
          to="/resites"
          className={({ isActive }) =>
            isActive ? "sidebar__link sidebar__link--active" : "sidebar__link"
          }
        >
          Пересдачи
        </NavLink>

        <NavLink
          to="/statements"
          className={({ isActive }) =>
            isActive ? "sidebar__link sidebar__link--active" : "sidebar__link"
          }
        >
          Ведомости
        </NavLink>

        <button
          className="sidebar__logout"
          type="button"
          onClick={handleLogout}
        >
          ↪ Выход
        </button>
      </nav>
    </aside>
  );
}

export default Sidebar;
