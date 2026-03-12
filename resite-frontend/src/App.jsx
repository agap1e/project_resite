import { Navigate, Route, Routes } from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import ResitesPage from "./pages/ResitesPage";
import ResiteDetailsPage from "./pages/ResiteDetailsPage";
import StatementsPage from "./pages/StatementsPage";
import ProtectedRoute from "./components/ProtectedRoute";

function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="/login" element={<LoginPage />} />

      <Route
        path="/resites"
        element={
          <ProtectedRoute>
            <ResitesPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/resites/:id"
        element={
          <ProtectedRoute>
            <ResiteDetailsPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/statements"
        element={
          <ProtectedRoute>
            <StatementsPage />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

export default App;
