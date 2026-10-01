import { RouterProvider } from "react-router-dom";
import { router } from "./routes/Router";
import { Toaster } from "sonner";

import { useTheme } from "@/app/providers/useTheme";

export default function App() {
  const { resolvedTheme } = useTheme();
  return (
    <>
      <RouterProvider router={router} />
      <Toaster
        richColors
        position="top-right"
        theme={resolvedTheme}
        toastOptions={{
          // El botón de acción de sonner es negro por defecto: aquí se pinta como
          // un botón `outline` de la interfaz. Con `!`, porque los estilos de
          // sonner usan selectores de atributo más específicos que una clase.
          classNames: {
            actionButton:
              "h-7! rounded-md! border! border-border! bg-background! px-2.5! text-xs! font-medium! text-foreground! shadow-xs! hover:bg-muted! focus-visible:ring-[3px]! focus-visible:ring-ring/50!",
          },
        }}
      />
    </>
  );
}
