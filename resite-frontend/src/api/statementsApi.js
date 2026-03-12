import { statements as initialStatements } from "../data/mockData";

const STORAGE_KEY = "statements";

function delay(ms = 300) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function getStoredStatements() {
  const raw = localStorage.getItem(STORAGE_KEY);

  if (!raw) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(initialStatements));
    return [...initialStatements];
  }

  return JSON.parse(raw);
}

function saveStatements(statements) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(statements));
}

export async function getStatements(semester = null) {
  await delay();

  const allStatements = getStoredStatements();

  if (!semester) {
    return allStatements;
  }

  return allStatements.filter((item) => item.semester === semester);
}

export async function createStatementFromResite(resite) {
  await delay();

  const allStatements = getStoredStatements();

  const alreadyExists = allStatements.some(
    (item) =>
      item.discipline === resite.discipline &&
      item.date === resite.date &&
      item.kind === resite.type
  );

  if (alreadyExists) {
    return allStatements;
  }

  const newStatement = {
    id: Date.now(),
    number: String(Date.now()).slice(-8),
    type: "Аттестационная ведомость",
    kind: resite.type,
    discipline: resite.discipline,
    date: resite.date,
    group: resite.groupsFull[0] || "—",
    educationForm: "Очная",
    semester: resite.semester,
  };

  const updatedStatements = [...allStatements, newStatement];
  saveStatements(updatedStatements);

  return updatedStatements;
}
