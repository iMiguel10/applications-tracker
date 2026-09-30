import { createBrowserRouter, Navigate } from "react-router-dom";

import { PageFallback } from "@/shared/components/common/PageFallback";
import { AppLayout } from "@/shared/components/layout/AppLayout";
import { ApplicationDetailPage } from "../pages/ApplicationDetailPage";
import { ApplicationEditPage } from "../pages/ApplicationEditPage";
import { ApplicationNewPage } from "../pages/ApplicationNewPage";
import { ApplicationsPage } from "../pages/ApplicationsPage";
import { CompaniesPage } from "../pages/CompaniesPage";
import { DashboardPage } from "../pages/DashboardPage";
import { DocumentsPage } from "../pages/DocumentsPage";
import { ForgotPasswordPage } from "../pages/ForgotPasswordPage";
import { HealthPage } from "../pages/HealthPage";
import { LoginPage } from "../pages/LoginPage";
import { PreferencesPage } from "../pages/PreferencesPage";
import { RegisterPage } from "../pages/RegisterPage";
import { RemindersPage } from "../pages/RemindersPage";
import { ResetPasswordPage } from "../pages/ResetPasswordPage";
import { VerifyEmailPage } from "../pages/VerifyEmailPage";
import { UnsubscribePage } from "../pages/UnsubscribePage";
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
  {
    path: "/forgot-password",
    element: <ForgotPasswordPage />,
    loader: redirectIfAuthenticatedLoader,
    HydrateFallback: PageFallback,
  },
  // Sin loader: el enlace del email tiene que funcionar también con una sesión
  // abierta en este navegador (al guardar se cierran todas).
  { path: "/reset-password", element: <ResetPasswordPage /> },
  // Sin loader: el enlace se puede abrir con o sin sesión, en cualquier dispositivo.
  { path: "/verify-email", element: <VerifyEmailPage /> },
  // Sin loader: la baja de avisos funciona sin sesión y con cualquier sesión (RF-85).
  { path: "/unsubscribe", element: <UnsubscribePage /> },
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
      { path: "/documents", element: <DocumentsPage /> },
      { path: "/preferences", element: <PreferencesPage /> },
    ],
  },
]);
