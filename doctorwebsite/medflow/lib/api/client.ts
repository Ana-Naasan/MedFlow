import createClient, { type Middleware } from "openapi-fetch";
import createQueryClient from "openapi-react-query";

import type { paths } from "./generated";

export const apiClient = createClient<paths>({
  baseUrl: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000",
});

/**
 * Per-request bearer-token middleware. The token is read from the environment
 * on every request (not frozen at module load) so the Authorization header is
 * applied per-request and omitted entirely when no token is configured.
 */
export const bearerMiddleware: Middleware = {
  onRequest({ request }) {
    const token = process.env.NEXT_PUBLIC_API_TOKEN;
    if (token) {
      request.headers.set("Authorization", `Bearer ${token}`);
    }
    return request;
  },
};

apiClient.use(bearerMiddleware);

export const $api = createQueryClient(apiClient);
