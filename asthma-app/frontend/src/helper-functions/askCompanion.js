import { API_URL } from "../config.js";

// Bounded successful exchanges live only in the current browser session.
export async function askCompanion({ token, message, persona = "warm", includeSavedContext = false, history = [], contextToken = null }) {
  const response = await fetch(`${API_URL}/v1/companion/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ message, persona, include_saved_context: includeSavedContext, history, context_token: contextToken }),
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(typeof data?.detail === "string" ? data.detail : "Unable to reach the companion. Please try again.");
    error.status = response.status;
    throw error;
  }
  if (typeof data?.message !== "string" || !data.message.trim()) {
    throw new Error("The companion returned an empty reply. Please try again.");
  }
  return data;
}

export function boundedHistory(history) {
  const recent = history.slice(-8);
  while (recent.reduce((size, item) => size + item.content.length, 0) > 6000) recent.splice(0, 2);
  return recent;
}
