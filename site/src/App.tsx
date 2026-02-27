import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AnalyticsLoader } from "@/components/AnalyticsLoader";
import { CookieBanner } from "@/components/CookieBanner";
import { Footer } from "@/components/Footer";
import { Error } from "@/routes/Error";
import { Imprint } from "@/routes/Imprint";
import { Landing } from "@/routes/Landing";
import { Privacy } from "@/routes/Privacy";
import { Success } from "@/routes/Success";
function App() {
  return (
    <BrowserRouter>
      <AnalyticsLoader />
      <div className="min-h-screen flex flex-col">
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/success" element={<Success />} />
            <Route path="/error" element={<Error />} />
            <Route path="/privacy" element={<Privacy />} />
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
