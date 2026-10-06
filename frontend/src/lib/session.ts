// Session cache ownership: the server holds the httpOnly cookie, this module owns the
// react-query cache around it. Never hand-roll logout — a stale cache leaks the previous
// account's data to the next login on this browser.
import { apiPost } from "@/lib/api";
import { queryClient } from "@/lib/queryClient";

export async function beginSession() {
  await queryClient.invalidateQueries();
}

export async function endSession() {
  try {
    await apiPost("/auth/logout");
  } finally {
    queryClient.clear();
  }
}
