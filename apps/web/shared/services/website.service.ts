import { apiPost } from "@/shared/lib/api";
import type { WebsiteResponse } from "@/shared/types/ai";

export const websiteService = {
  createFromUrl(url: string): Promise<WebsiteResponse> {
    return apiPost<WebsiteResponse>("/websites", { url });
  },
};
