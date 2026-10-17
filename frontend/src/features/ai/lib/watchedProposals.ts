import { useSyncExternalStore } from "react";

import type { AiTask } from "../types/Ai";

/**
 * Propuestas de IA que esta pestaña pidió y aún no ha avisado de que terminaron.
 * El vigilante de `AppLayout` (`AiProposalWatcher`) las consulta desde cualquier
 * página y avisa al terminar. Se guardan en `sessionStorage`: sobreviven a una
 * recarga, pero no salen de la pestaña (para lo demás está el aviso por email).
 *
 * Llevan el usuario porque el logout no pasa por aquí: el vigilante descarta las
 * de otra cuenta en vez de consultarlas.
 */
export interface WatchedProposal {
  proposalId: string;
  applicationId: string;
  userId: string;
  kind: AiTask;
  position: string;
  company: string;
}

/** Lo bastante para leer el aviso si se estaba mirando otra cosa. */
export const PROPOSAL_TOAST_MS = 10_000;

export const reviewPath = (applicationId: string, proposalId: string) =>
  `/applications/${applicationId}/ai/${proposalId}`;

const STORAGE_KEY = "ai.watchedProposals";
const listeners = new Set<() => void>();
let cache: WatchedProposal[] | null = null;

function read(): WatchedProposal[] {
  if (cache) return cache;
  try {
    const parsed: unknown = JSON.parse(sessionStorage.getItem(STORAGE_KEY) ?? "[]");
    cache = Array.isArray(parsed) ? (parsed as WatchedProposal[]) : [];
  } catch {
    // Sin almacenamiento (modo privado estricto): se vigila solo en memoria.
    cache = [];
  }
  return cache;
}

function write(next: WatchedProposal[]) {
  cache = next;
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {
    // Igual que al leer: la lista en memoria sigue valiendo para esta página.
  }
  listeners.forEach((listener) => listener());
}

export function watchProposal(entry: WatchedProposal) {
  const others = read().filter((item) => item.proposalId !== entry.proposalId);
  write([...others, entry]);
}

export function unwatchProposal(proposalId: string) {
  const current = read();
  if (current.some((item) => item.proposalId === proposalId)) {
    write(current.filter((item) => item.proposalId !== proposalId));
  }
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useWatchedProposals(): WatchedProposal[] {
  return useSyncExternalStore(subscribe, read);
}

/** Solo para las pruebas: vuelve a leer del almacenamiento. */
export function resetWatchedProposalsCache() {
  cache = null;
}
