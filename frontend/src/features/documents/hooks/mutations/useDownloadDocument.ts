import { useMutation } from "@tanstack/react-query";
import { downloadBlob } from "@/shared/lib/download";
import { downloadName } from "../../lib/fileName";
import { documentService } from "../../services/document.service";
import type { LibraryDocument } from "../../types/Document";

export function useDownloadDocument() {
  return useMutation({
    mutationFn: (document: LibraryDocument) => documentService.file(document.id),
    onSuccess: (blob, document) => downloadBlob(blob, downloadName(document.name)),
  });
}
