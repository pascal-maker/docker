import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Landing } from "@/routes/Landing";
import { Success } from "@/routes/Success";
import { Error } from "@/routes/Error";
import { Privacy } from "@/routes/Privacy";
import { Terms } from "@/routes/Terms";
import { Imprint } from "@/routes/Imprint";
import { CookieBanner } from "@/components/CookieBanner";
import { Footer } from "@/components/Footer";

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col">
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/success" element={<Success />} />
            <Route path="/error" element={<Error />} />
            <Route path="/privacy" element={<Privacy />} />
            <Route path="/terms" element={<Terms />} />
            <Route path="/imprint" element={<Imprint />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
        <Footer />
        <CookieBanner />
      </div>
    </BrowserRouter>
  );
}

export default App;
