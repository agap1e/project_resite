import { resites, semesters } from "../data/mockData";

function delay(ms = 300) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function getSemesters() {
  await delay();
  return semesters;
}

export async function getResites(semester = null) {
  await delay();

  if (!semester) {
    return resites;
  }

  return resites.filter((item) => item.semester === semester);
}

export async function getResiteById(id) {
  await delay();

  const numericId = Number(id);
  const resite = resites.find((item) => item.id === numericId);

  if (!resite) {
    throw new Error("Пересдача не найдена");
  }

  return resite;
}
