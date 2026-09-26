import { API_URL } from "../config";

async function parseResponse(response, fallbackMessage) {
  const data = await response.json();

  if (!response.ok) {
    const message =
      typeof data?.detail === "string"
        ? data.detail
        : data?.detail?.message || fallbackMessage;

    const error = new Error(message);
    error.code = data?.detail?.code || data?.code;
    error.status = response.status;
    throw error;
  }

  return data;
}

export async function getCheckIns({ from, to, token }) {
  const params = new URLSearchParams();

  if (from) params.set("from", from);
  if (to) params.set("to", to);

  const response = await fetch(
    `${API_URL}/v1/check-ins?${params.toString()}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  return parseResponse(response, "Failed to load check-ins");
}

export async function saveCheckIn({ token, checkIn }) {
  const response = await fetch(`${API_URL}/v1/check-ins`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(checkIn),
  });

  return parseResponse(response, "Failed to save check-in");
}

export async function logInhalerPuff({ token, date }) {
  const response = await fetch(
    `${API_URL}/v1/check-ins/inhaler/puff`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        ...(date ? { date } : {}),
      }),
    }
  );

  return parseResponse(
    response,
    "Failed to log rescue inhaler use"
  );
}