import Sidebar from "./Sidebar";

function AppShell({
  title,
  children,
  semester,
  onSemesterClick,
  semesterDropdown,
}) {
  return (
    <div className="page page--shell">
      <Sidebar />

      <main className="content-card">
        <header className="content-card__header">
          <h1>{title}</h1>

          {semester ? (
            <div className="semester-control">
              <button
                type="button"
                className="semester-chip"
                onClick={onSemesterClick}
              >
                {semester}
              </button>

              {semesterDropdown}
            </div>
          ) : null}
        </header>

        {children}
      </main>
    </div>
  );
}

export default AppShell;
