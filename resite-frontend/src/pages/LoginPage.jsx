import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../api/authApi";

function LoginPage() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    login: "",
    password: "",
  });

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((prev) => ({
      ...prev,
      [name]: value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();

    try {
      setLoading(true);
      setError("");

      await login(form);

      localStorage.setItem("auth", "true");

      navigate("/resites");
    } catch (err) {
      setError(err.message || "Ошибка входа");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page page--login">
      <div className="login-panel">
        <div className="login-card">
          <h1>Вход</h1>

          <form className="login-form" onSubmit={handleSubmit}>
            <label>
              Логин
              <input
                type="text"
                name="login"
                value={form.login}
                onChange={handleChange}
              />
            </label>

            <label>
              Пароль
              <input
                type="password"
                name="password"
                value={form.password}
                onChange={handleChange}
              />
            </label>

            {error && <p className="form-error">{error}</p>}

            <button
              type="submit"
              className="primary-link-button"
              disabled={loading}
            >
              {loading ? "Вход..." : "Войти"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default LoginPage;
