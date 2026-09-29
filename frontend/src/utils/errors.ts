import { isAxiosError } from "axios";
import type { ApiErrorBody } from "../types";

/** Turn any thrown value (usually an Axios error) into a message suitable for the UI. */
export function getErrorMessage(error: unknown, fallback = "Something went wrong. Please try again."): string {
  if (isAxiosError<ApiErrorBody>(error)) {
    if (!error.response) {
      return "Cannot reach the server. Check that the backend is running and VITE_API_URL is correct.";
    }
    const detail = error.response.data?.detail;
    if (typeof detail === "string" && detail) return detail;
    if (Array.isArray(detail) && detail.length) return detail.map((d) => d.msg).join("; ");
    if (error.response.status === 403) return "You do not have permission to perform this action.";
    if (error.response.status >= 500) return "The server encountered an error. Please try again.";
  }
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}

export function getErrorCode(error: unknown): string | undefined {
  return isAxiosError<ApiErrorBody>(error) ? error.response?.data?.code : undefined;
}
