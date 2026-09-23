import { useQuery } from "@tanstack/react-query";
import { interviewKeys } from "../../interview.keys";
import { interviewService } from "../../services/interview.service";

export function useInterviews(applicationId: string) {
  return useQuery({
    queryKey: interviewKeys.all(applicationId),
    queryFn: () => interviewService.list(applicationId),
  });
}
