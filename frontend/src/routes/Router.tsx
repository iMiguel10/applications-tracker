import { createBrowserRouter, Navigate } from "react-router-dom";

import { PageFallback } from "@/shared/components/common/PageFallback";
import { AppLayout } from "@/shared/components/layout/AppLayout";
import { ApplicationsPage } from "../pages/ApplicationsPage";
import { HealthPage } from "../pages/HealthPage";
import { LoginPage } from "../pages/LoginPage";
import { RegisterPage } from "../pages/RegisterPage";
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
      { path: "/", element: <Navigate to="/applications" replace /> },
      { path: "/applications", element: <ApplicationsPage /> },
    ],
  },
]);
