import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import { Layout } from "./components/Layout";
import { HomePage } from "./pages/HomePage";
import { SettingsPage } from "./pages/SettingsPage";
import { CatalogPage } from "./pages/CatalogPage";
import { NewTaskPage } from "./pages/NewTaskPage";
import { FieldConfirmPage } from "./pages/FieldConfirmPage";
import { RunBoardPage } from "./pages/RunBoardPage";
import { RunsPage } from "./pages/RunsPage";
import { ExportPage } from "./pages/ExportPage";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/catalog" element={<CatalogPage />} />
          <Route path="/tasks/new" element={<NewTaskPage />} />
          <Route path="/tasks/:taskId/fields" element={<FieldConfirmPage />} />
          <Route path="/runs" element={<RunsPage />} />
          <Route path="/runs/:taskId" element={<RunBoardPage />} />
          <Route path="/export" element={<ExportPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
);
