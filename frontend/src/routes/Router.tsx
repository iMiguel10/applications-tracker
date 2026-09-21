import { createBrowserRouter } from "react-router-dom";
import { HealthPage } from "../pages/HealthPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <HealthPage />,
  },
]);
