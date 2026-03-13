const API_BASE = "http://127.0.0.1:8000/api";

function formatDate(dateString) {
  if (!dateString) return "";
  const [year, month, day] = dateString.split("-");
  return `${day}.${month}.${year.slice(-2)}`;
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

function mapRetake(item) {
  return {
    id: item.id,
    semester: "Не указан",
    date: formatDate(item.retake_date),
    time: item.retake_time ?? "",
    discipline: item.subject?.name ?? "—",
    type: mapWorkType(item.subject?.work_type),
    groupsShort: "—",
    groupsFull: [],
    lecturer: item.lecturer ?? "—",
    commission: item.commission ?? "—",
    staff: [],
    link: item.retake_link ?? "",
    statementsCreated: false,
  };
}

export async function getSemesters() {
  return ["Не указан"];
}

export async function getResites(semester = null) {
  const response = await fetch(`${API_BASE}/retakes/`);

  if (!response.ok) {
    throw new Error("Не удалось загрузить пересдачи");
  }

  const data = await response.json();
  const mapped = data.map(mapRetake);

  if (!semester || semester === "Не указан") {
    return mapped;
  }

  return mapped.filter((item) => item.semester === semester);
}

export async function getResiteById(id) {
  const response = await fetch(`${API_BASE}/retakes/${id}/`);

  if (!response.ok) {
    throw new Error("Пересдача не найдена");
  }

  const data = await response.json();
  return mapRetake(data);
}