import { useState } from "react";

import type { ApplicationStatus } from "@/features/applications/types/Application";

const STORAGE_KEY = "board.collapsed";

function readStored(): ApplicationStatus[] {
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]");
    return Array.isArray(parsed) ? (parsed as ApplicationStatus[]) : [];
  } catch {
    return [];
  }
}

/**
 * Columnas plegadas del tablero (RF-122). Es una comodidad de este navegador, como
 * el tema: no va en la cuenta, y si el almacenamiento falla todas salen desplegadas.
 */
export function useCollapsedColumns() {
  const [collapsed, setCollapsed] = useState<ApplicationStatus[]>(readStored);

  const toggle = (status: ApplicationStatus) =>
    setCollapsed((current) => {
      const next = current.includes(status)
        ? current.filter((item) => item !== status)
        : [...current, status];
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {
        // Sin almacenamiento, el plegado dura lo que la página.
      }
      return next;
    });

  return { isCollapsed: (status: ApplicationStatus) => collapsed.includes(status), toggle };
}
