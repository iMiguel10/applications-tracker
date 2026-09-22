import { createBrowserRouter, Navigate } from "react-router-dom";
import { ApplicationsPage } from "../pages/ApplicationsPage";
import { HealthPage } from "../pages/HealthPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Navigate to="/applications" replace />,
  },
  {
    path: "/applications",
    element: <ApplicationsPage />,
  },
  {
    path: "/health",
    element: <HealthPage />,
  },
]);
