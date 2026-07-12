import axios from "axios";

/**
 * Shared Axios client for SitePilot API.
 * Base URL from NEXT_PUBLIC_API_URL (see apps/web/.env.example).
 */

export const axiosClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1",
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
  timeout: 30_000,
});

axiosClient.interceptors.request.use((config) => {
  config.headers.set("Accept", "application/json");
  return config;
});

axiosClient.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(error),
);
