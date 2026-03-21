import { BrowserRouter, Routes, Route } from "react-router-dom";
import RunsPage from "./pages/RunPage";
import RunDetailPage from "./pages/RunDetailPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<RunsPage />} />
        <Route path="/runs/:runId" element={<RunDetailPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;



