import { useEffect, useState } from "react";
import AppShell from "../components/layout/AppShell";
import { getStatements } from "../api/statementsApi";
import { getSemesters } from "../api/resitesApi";

function StatementsPage() {
  const [semesters, setSemesters] = useState([]);
  const [selectedSemester, setSelectedSemester] = useState("");
  const [statements, setStatements] = useState([]);
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

        const statementsData = await getStatements(initialSemester);
        setStatements(statementsData);
      } catch (err) {
        setError(err.message || "Ошибка загрузки ведомостей");
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

      const data = await getStatements(semester);
      setStatements(data);
    } catch (err) {
      setError(err.message || "Ошибка фильтрации ведомостей");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppShell
      title="Ведомости"
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

      {!loading && !error && statements.length === 0 && (
        <p>Нет доступных ведомостей</p>
      )}

      {!loading && !error && statements.length > 0 && (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Номер</th>
                <th>Тип</th>
                <th>Вид</th>
                <th>Дисциплина</th>
                <th>Дата</th>
                <th>Группа</th>
                <th>Форма обучения</th>
              </tr>
            </thead>
            <tbody>
              {statements.map((item) => (
                <tr key={item.id} className="table-row">
                  <td>{item.number}</td>
                  <td>{item.type}</td>
                  <td>{item.kind}</td>
                  <td>{item.discipline}</td>
                  <td>{item.date}</td>
                  <td>{item.group}</td>
                  <td>{item.educationForm}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </AppShell>
  );
}

export default StatementsPage;
