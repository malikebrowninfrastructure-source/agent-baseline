import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import RunsPage from "./pages/RunPage";
import RunDetailPage from "./pages/RunDetailPage";
import ApprovalsPage from "./pages/ApprovalsPage";

function App() {
  return (
    <BrowserRouter>
      <nav style={{
        padding: "8px 24px", borderBottom: "1px solid #e0e0e0",
        display: "flex", gap: "20px", background: "#fafafa",
      }}>
        <Link to="/" style={{ fontWeight: "600", textDecoration: "none", color: "#1a1a1a" }}>Runs</Link>
        <Link to="/approvals" style={{ fontWeight: "600", textDecoration: "none", color: "#1a1a1a" }}>Approvals</Link>
      </nav>
      <Routes>
        <Route path="/" element={<RunsPage />} />
        <Route path="/runs/:runId" element={<RunDetailPage />} />
        <Route path="/approvals" element={<ApprovalsPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
