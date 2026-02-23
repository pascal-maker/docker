import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Landing } from "@/routes/Landing";
import { Success } from "@/routes/Success";
import { Error } from "@/routes/Error";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/success" element={<Success />} />
        <Route path="/error" element={<Error />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
