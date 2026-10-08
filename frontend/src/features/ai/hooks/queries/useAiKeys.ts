import { useQuery } from "@tanstack/react-query";
import { aiKeys } from "../../ai.keys";
import { aiService } from "../../services/ai.service";

/** Las claves propias guardadas (sin la clave) y cuál se usa (RF-151). */
export function useAiKeys() {
  return useQuery({ queryKey: aiKeys.keys(), queryFn: aiService.keys });
}
