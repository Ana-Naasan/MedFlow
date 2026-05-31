import createClient from "openapi-fetch";

import type { paths } from "./generated";

const token = process.env.NEXT_PUBLIC_API_TOKEN;

export const apiClient = createClient<paths>({
  baseUrl: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000",
  headers: token ? { Authorization: `Bearer ${token}` } : {},
});