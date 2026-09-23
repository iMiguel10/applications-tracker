import { useMutation } from "@tanstack/react-query";
import { downloadBlob } from "@/shared/lib/download";
import { applicationService } from "../../services/application.service";

export function useExportApplications() {
  return useMutation({
    mutationFn: applicationService.exportCsv,
    onSuccess: (blob) => downloadBlob(blob, "applications.csv"),
  });
}
