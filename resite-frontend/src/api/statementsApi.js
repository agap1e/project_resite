const API_BASE = "http://127.0.0.1:8000/api";
const USER_ID = 1;

function formatDate(dateString) {
  if (!dateString) return "";
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) return dateString;

  const day = String(date.getDate()).padStart(2, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const year = String(date.getFullYear()).slice(-2);

  return `${day}.${month}.${year}`;
}

function mapWorkType(workType) {
  switch (workType) {
    case "exam":
      return "Экзамен";
    case "credit":
      return "Зачет";
    case "course_project":
      return "Курсач";
    default:
      return workType || "—";
  }
}

function flattenStatements(statements) {
  return statements.flatMap((statement) =>
    (statement.items || []).map((item) => ({
      id: `${statement.id}-${item.id}`,
      number: String(statement.id).padStart(8, "0"),
      type: "Аттестационная ведомость",
      kind: mapWorkType(item.subject?.work_type),
      discipline: item.subject?.name ?? "—",
      date: formatDate(statement.created_at),
      group: "—",
      educationForm: "Очная",
      semester: "Не указан",
      isActive: statement.is_active,
    }))
  );
}

export async function getStatements(semester = null) {
  const response = await fetch(`${API_BASE}/statements/?user_id=${USER_ID}`);

  if (!response.ok) {
    throw new Error("Не удалось загрузить ведомости");
  }

  const data = await response.json();
  const flattened = flattenStatements(data);

  if (!semester || semester === "Не указан") {
    return flattened;
  }

  return flattened.filter((item) => item.semester === semester);
}

export async function createStatementFromResite(resite) {
  const response = await fetch(
    `${API_BASE}/statements/create/${resite.id}/`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ user_id: USER_ID }),
    }
  );

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || "Не удалось создать ведомость");
  }

  const data = await response.json();
  return data.statement;
}