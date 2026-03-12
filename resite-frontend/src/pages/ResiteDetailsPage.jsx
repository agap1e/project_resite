import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import AppShell from "../components/layout/AppShell";
import { getResiteById } from "../api/resitesApi";
import { createStatementFromResite } from "../api/statementsApi";

function ResiteDetailsPage() {
  const { id } = useParams();

  const [resite, setResite] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [statementsCreated, setStatementsCreated] = useState(false);

  useEffect(() => {
    async function loadResite() {
      try {
        setLoading(true);
        setError("");

        const data = await getResiteById(id);
        setResite(data);
        setStatementsCreated(data.statementsCreated);
      } catch (err) {
        setError(err.message || "Ошибка загрузки информации");
      } finally {
        setLoading(false);
      }
    }

    loadResite();
  }, [id]);

  async function handleCreateStatements() {
    try {
      await createStatementFromResite(resite);
      setStatementsCreated(true);
    } catch (err) {
      setError(err.message || "Ошибка формирования ведомостей");
    }
  }

  return (
    <AppShell title="Подробная информация">
      {loading && <p>Загрузка...</p>}
      {error && <p>{error}</p>}

      {!loading && !error && resite && (
        <div className="details-card">
          <div className="details-list">
            <p>
              <strong>Дата:</strong> {resite.date}
            </p>
            <p>
              <strong>Время:</strong> {resite.time}
            </p>
            <p>
              <strong>Дисциплина:</strong> {resite.discipline}
            </p>
            <p>
              <strong>Тип:</strong> {resite.type}
            </p>
            <p>
              <strong>Лектор:</strong> {resite.lecturer}
            </p>
            <p>
              <strong>Группы:</strong> {resite.groupsFull.join(", ")}
            </p>
            <p>
              <strong>Комиссия:</strong> {resite.commission}
            </p>
            <p>
              <strong>Сотрудники:</strong> {resite.staff.join(", ")}
            </p>
            <p>
              <strong>Ссылка:</strong>{" "}
              <a href={resite.link} target="_blank" rel="noreferrer">
                {resite.link}
              </a>
            </p>
          </div>

          <div className="details-actions">
            <Link to="/resites" className="text-link">
              Назад
            </Link>

            {statementsCreated ? (
              <span className="status-text">Ведомости сформированы</span>
            ) : (
              <button
                type="button"
                className="secondary-button"
                onClick={handleCreateStatements}
              >
                Сформировать ведомости
              </button>
            )}
          </div>
        </div>
      )}
    </AppShell>
  );
}

export default ResiteDetailsPage;
