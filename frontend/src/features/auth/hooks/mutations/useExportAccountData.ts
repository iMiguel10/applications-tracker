import { useMutation } from "@tanstack/react-query";
import { format } from "date-fns";

import { downloadBlob } from "@/shared/lib/download";
import { authService } from "../../services/auth.service";

/** Descarga el `.zip` con todos los datos de la cuenta (issue #4). Con
 * `apiClient.getBlob` y no con un enlace: solo el SDK refresca un access token
 * caducado, y un enlace normal daría 401 pasados 5 minutos. */
export function useExportAccountData() {
  return useMutation({
    mutationFn: () => authService.exportData(),
    onSuccess: (blob) =>
      downloadBlob(blob, `applications-tracker-export-${format(new Date(), "yyyy-MM-dd")}.zip`),
  });
}
