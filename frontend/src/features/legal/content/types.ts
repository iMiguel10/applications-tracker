import type { ReactNode } from "react";

import type { LegalInfo } from "@/features/meta/types/Meta";
import type { LegalPage } from "../lib/legalPages";

/** Lo que cambia el texto de una instalación a otra: su responsable y lo que tiene
 * activo. Los textos nunca inventan nada que no esté aquí. */
export interface LegalContext {
  legal: LegalInfo;
  emailEnabled: boolean;
  /** El origen de la instalación (https://…), para nombrarla. */
  site: string;
}

export type LegalContent = Record<LegalPage, (context: LegalContext) => ReactNode>;
