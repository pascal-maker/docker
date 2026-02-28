import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { OrgSelector } from "@/routes/OrgSelector.tsx";
import { IssuesList } from "@/routes/IssuesList.tsx";
import { IssueDetail } from "@/routes/IssueDetail.tsx";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<OrgSelector />} />
        <Route path="/orgs/:orgId/issues" element={<IssuesList />} />
        <Route path="/orgs/:orgId/issues/:runId" element={<IssueDetail />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
