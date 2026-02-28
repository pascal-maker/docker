import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AnalyticsLoader } from "@/components/AnalyticsLoader.tsx";
import { CookieBanner } from "@/components/CookieBanner.tsx";
import { Footer } from "@/components/Footer.tsx";
import { AuthSignIn } from "@/routes/AuthSignIn.tsx";
import { AuthSuccess } from "@/routes/AuthSuccess.tsx";
import { Error } from "@/routes/Error.tsx";
import { Imprint } from "@/routes/Imprint.tsx";
import { Landing } from "@/routes/Landing.tsx";
import { Privacy } from "@/routes/Privacy.tsx";
import { Success } from "@/routes/Success.tsx";
function App() {
  return (
    <BrowserRouter>
      <AnalyticsLoader />
      <div className="min-h-screen flex flex-col">
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/success" element={<Success />} />
            <Route path="/auth/signin" element={<AuthSignIn />} />
            <Route path="/auth/success" element={<AuthSuccess />} />
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
