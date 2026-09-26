import { API_URL } from "../config";

/**
 * Ask the Asthma Copilot a one-off question/statement over today's cached forecast.
 * Does not overwrite Home-card advice on the server.
 */
export async function askCopilot({ token, message, date }) {
  const response = await fetch(`${API_URL}/v1/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      message,
      ...(date ? { date } : {}),
    }),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const error = new Error(
      typeof data?.detail === "string"
        ? data.detail
        : data?.detail?.message || "Unable to reach Copilot right now."
    );
    error.code = data?.code || data?.detail?.code;
    error.status = response.status;
    throw error;
  }

  if (!data?.advice) {
    const error = new Error(
      (Array.isArray(data?.warnings) && data.warnings[0]) ||
        "Copilot could not generate a reply right now."
    );
    error.code = "ADVICE_UNAVAILABLE";
    error.status = response.status;
    throw error;
  }

  return data;
}

/**
 * Chat bubble text: use the conversational summary; append one short tip section if present.
 */
export function formatCopilotReply(advice) {
  if (!advice || typeof advice !== "object") {
    return "";
  }
  const summary = String(advice.summary || "").trim();
  const firstBody = String(advice.sections?.[0]?.body || "").trim();
  if (summary && firstBody && firstBody !== summary) {
    return `${summary}\n\n${firstBody}`;
  }
  return summary || firstBody || "I could not form a reply from the available context.";
}
