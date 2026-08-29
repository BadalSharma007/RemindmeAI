export function friendlyError(error: any): string {
  if (!error) return "An unexpected error occurred.";

  if (typeof error === "string") return error;

  if (error.response) {
    const status = error.response.status;
    const data = error.response.data;

    if (status === 400) {
      return data?.detail || "Invalid request. Please check your input.";
    }
    if (status === 401) {
      return "Your session has expired. Please sign in again.";
    }
    if (status === 403) {
      return "You do not have permission to perform this action.";
    }
    if (status === 404) {
      return "The requested item was not found.";
    }
    if (status === 422) {
      if (Array.isArray(data?.detail)) {
        return data.detail.map((e: any) => e.msg || e.message).join(", ");
      }
      return data?.detail || "Validation failed. Please verify the submitted data.";
    }
    if (status === 429) {
      return "Too many requests. Please wait a moment and try again.";
    }
    if (status >= 500) {
      return "Server error. We are working on resolving this, please try again shortly.";
    }
  }

  if (error.code === "ECONNABORTED" || error.message?.includes("timeout")) {
    return "Request timed out. Please check your internet connection.";
  }

  if (error.message === "Network Error" || !navigator.onLine) {
    return "No internet connection detected. Please check your network.";
  }

  return error.message || "An unexpected error occurred.";
}
