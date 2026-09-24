import { useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { useForceLightTheme } from "@/app/providers/useForceLightTheme";
import { AuthShowcase } from "./AuthShowcase";

interface AuthLayoutProps {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer: ReactNode;
}

/** Escala la ilustración del panel al hueco que deja el lema, para que en pantallas
 * bajas se vea entera (más pequeña) en vez de cortarse o desaparecer. `offsetHeight`
 * no cuenta el `transform`, así que siempre mide el tamaño natural. */
function useFitShowcase() {
  const containerRef = useRef<HTMLDivElement>(null);
  const headlineRef = useRef<HTMLParagraphElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const [fit, setFit] = useState({ scale: 1, height: 0 });

  useLayoutEffect(() => {
    const container = containerRef.current;
    const headline = headlineRef.current;
    const content = contentRef.current;
    if (!container || !headline || !content) return;

    // ResizeObserver avisa antes del primer pintado, así que no hay salto visible.
    const observer = new ResizeObserver(() => {
      const styles = getComputedStyle(container);
      const available =
        container.clientHeight -
        parseFloat(styles.paddingTop) -
        parseFloat(styles.paddingBottom) -
        (parseFloat(styles.rowGap) || 0) -
        headline.offsetHeight;
      const natural = content.offsetHeight;
      if (natural === 0) return;
      const scale = Math.max(0, Math.min(1, available / natural));
      setFit({ scale, height: natural * scale });
    });
    observer.observe(container);
    observer.observe(headline);
    observer.observe(content);
    return () => observer.disconnect();
  }, []);

  return { containerRef, headlineRef, contentRef, ...fit };
}

/** Marco compartido de login y registro: panel de marca en escritorio, cabecera
 * compacta en móvil. Siempre en claro (F8.4): el panel de marca es oscuro fijo y el
 * formulario está pensado para leerse junto a él, así que el tema del usuario no se
 * aplica aquí (`useForceLightTheme`) — de lo contrario los dos paneles se funden en
 * modo oscuro y el contraste que sostiene el diseño desaparece. */
export function AuthLayout({ title, subtitle, children, footer }: AuthLayoutProps) {
  const { t } = useTranslation();
  useForceLightTheme();
  const { containerRef, headlineRef, contentRef, scale, height } = useFitShowcase();

  return (
    // En escritorio ocupa exactamente la ventana (sin scroll de página); en móvil puede
    // crecer si el teclado o un formulario largo lo necesitan.
    <div className="grid min-h-dvh bg-card lg:h-dvh lg:grid-cols-[1.1fr_1fr] lg:overflow-hidden">
      <div className="hidden min-h-0 flex-col bg-brand px-12 py-10 text-brand-foreground lg:flex xl:px-16">
        <span className="flex items-center gap-2.5 text-lg font-semibold tracking-tight">
          <img src="/brand/logo.png" alt="" className="size-7" />
          {t("app.name")}
        </span>
        <div
          ref={containerRef}
          className="flex min-h-0 flex-1 flex-col justify-center gap-[min(2.5rem,5vh)] py-6"
        >
          <p
            ref={headlineRef}
            className="max-w-[18ch] text-[clamp(1.75rem,5vh,3rem)] leading-[1.1] font-semibold tracking-tight text-balance"
          >
            {t("app.tagline")}
          </p>
          <div className="shrink-0" style={{ height: height || undefined }}>
            <div
              ref={contentRef}
              className="origin-top-left"
              style={{ transform: `scale(${scale})` }}
            >
              <AuthShowcase />
            </div>
          </div>
        </div>
      </div>

      <div className="flex flex-col justify-center overflow-y-auto px-6 py-12 sm:px-12 lg:px-16">
        <div className="mx-auto w-full max-w-sm">
          {/* Dentro del bloque del formulario: así queda alineado con él a cualquier ancho. */}
          <span className="mb-12 flex items-center gap-2.5 lg:hidden">
            <img src="/brand/logo.png" alt="" className="size-7" />
            <span className="bg-gradient-to-r from-chart-1 to-chart-2 bg-clip-text text-lg font-semibold tracking-tight whitespace-nowrap text-transparent">
              {t("app.name")}
            </span>
          </span>
          <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
          <p className="mt-2 text-muted-foreground">{subtitle}</p>
          <div className="mt-8">{children}</div>
          <div className="mt-8 border-t pt-6">{footer}</div>
        </div>
      </div>
    </div>
  );
}
