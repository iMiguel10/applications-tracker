import { createBrowserRouter, Navigate } from "react-router-dom";

import { PageFallback } from "@/shared/components/common/PageFallback";
import { AppLayout } from "@/shared/components/layout/AppLayout";
import { ApplicationDetailPage } from "../pages/ApplicationDetailPage";
import { ApplicationEditPage } from "../pages/ApplicationEditPage";
import { ApplicationNewPage } from "../pages/ApplicationNewPage";
import { ApplicationsPage } from "../pages/ApplicationsPage";
import { CompaniesPage } from "../pages/CompaniesPage";
import { DashboardPage } from "../pages/DashboardPage";
import { HealthPage } from "../pages/HealthPage";
import { LoginPage } from "../pages/LoginPage";
import { PreferencesPage } from "../pages/PreferencesPage";
import { RegisterPage } from "../pages/RegisterPage";
import { RemindersPage } from "../pages/RemindersPage";
import { redirectIfAuthenticatedLoader, requireAuthLoader } from "./AuthLoaders";

// Toda ruta con loader declara HydrateFallback: es lo que se pinta en la primera
// carga mientras el loader (la comprobación de sesión) resuelve.
export const router = createBrowserRouter([
  // Públicas.
  {
    path: "/login",
    element: <LoginPage />,
    loader: redirectIfAuthenticatedLoader,
    HydrateFallback: PageFallback,
  },
  {
    path: "/register",
    element: <RegisterPage />,
    loader: redirectIfAuthenticatedLoader,
    HydrateFallback: PageFallback,
  },
  { path: "/health", element: <HealthPage /> },

  // Protegidas: el loader del layout se ejecuta en cada navegación a cualquier hija.
  {
    element: <AppLayout />,
    loader: requireAuthLoader,
    HydrateFallback: PageFallback,
    children: [
      { path: "/", element: <Navigate to="/dashboard" replace /> },
      { path: "/dashboard", element: <DashboardPage /> },
      { path: "/applications", element: <ApplicationsPage /> },
      { path: "/applications/new", element: <ApplicationNewPage /> },
      { path: "/applications/:applicationId", element: <ApplicationDetailPage /> },
      { path: "/applications/:applicationId/edit", element: <ApplicationEditPage /> },
      { path: "/companies", element: <CompaniesPage /> },
      { path: "/reminders", element: <RemindersPage /> },
      { path: "/preferences", element: <PreferencesPage /> },
    ],
  },
]);
