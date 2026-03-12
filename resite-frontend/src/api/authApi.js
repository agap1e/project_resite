function delay(ms = 300) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function login({ login, password }) {
  await delay();

  if (!login || !password) {
    throw new Error("Заполните логин и пароль");
  }

  return {
    id: 1,
    name: "Преподаватель",
    role: "teacher",
  };
}
