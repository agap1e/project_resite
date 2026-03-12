import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppShell from "../components/layout/AppShell";
import { getResites, getSemesters } from "../api/resitesApi";

function ResitesPage() {
  const navigate = useNavigate();

  const [semesters, setSemesters] = useState([]);
  const [selectedSemester, setSelectedSemester] = useState("");
  const [resites, setResites] = useState([]);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadInitialData() {
      try {
        setLoading(true);
        setError("");

        const semestersData = await getSemesters();
        setSemesters(semestersData);

        const initialSemester = semestersData[0] || "";
        setSelectedSemester(initialSemester);

        const resitesData = await getResites(initialSemester);
        setResites(resitesData);
      } catch (err) {
        setError(err.message || "Ошибка загрузки пересдач");
      } finally {
        setLoading(false);
      }
    }

    loadInitialData();
  }, []);

  async function handleSemesterSelect(semester) {
    try {
      setSelectedSemester(semester);
      setIsDropdownOpen(false);
      setLoading(true);

      const data = await getResites(semester);
      setResites(data);
    } catch (err) {
      setError(err.message || "Ошибка фильтрации");
    } finally {
      setLoading(false);
    }
  }

  function handleRowClick(id) {
    navigate(`/resites/${id}`);
  }

  return (
    <AppShell
      title="Пересдачи"
      semester={selectedSemester}
      onSemesterClick={() => setIsDropdownOpen((prev) => !prev)}
      semesterDropdown={
        isDropdownOpen ? (
          <div className="semester-dropdown">
            {semesters.map((semester) => (
              <button
                key={semester}
                type="button"
                className="semester-dropdown__item"
                onClick={() => handleSemesterSelect(semester)}
              >
                {semester}
              </button>
            ))}
          </div>
        ) : null
      }
    >
      {loading && <p>Загрузка...</p>}
      {error && <p>{error}</p>}

      {!loading && !error && resites.length === 0 && (
        <p>Нет доступных пересдач</p>
      )}

      {!loading && !error && resites.length > 0 && (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Дата</th>
                <th>Время</th>
                <th>Дисциплина</th>
                <th>Тип</th>
                <th>Группы</th>
              </tr>
            </thead>
            <tbody>
              {resites.map((item) => (
                <tr
                  key={item.id}
                  className="table-row table-row--clickable"
                  onClick={() => handleRowClick(item.id)}
                >
                  <td>{item.date}</td>
                  <td>{item.time}</td>
                  <td>{item.discipline}</td>
                  <td>{item.type}</td>
                  <td>{item.groupsShort}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </AppShell>
  );
}

export default ResitesPage;
