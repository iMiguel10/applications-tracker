import { useQuery } from "@tanstack/react-query";
import { aiKeys } from "../../ai.keys";
import { aiService } from "../../services/ai.service";

export function useAiConsents() {
  return useQuery({ queryKey: aiKeys.consents(), queryFn: aiService.consents });
}
