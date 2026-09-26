// Keep transport outcomes distinct: only an explicit 401 invalidates a session.
export async function requestProfile(url, token, fetcher = fetch) {
  try {
    const response = await fetcher(`${url}/v1/users/me`, {
      method: "GET",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (response.status === 401) return { status: "unauthorized" };
    if (!response.ok) return { status: "error", message: "Unable to retrieve profile. Please try again." };
    const profile = await response.json();
    if (!profile || typeof profile !== "object" || Array.isArray(profile)) {
      throw new Error("Invalid profile response");
    }
    return { status: "ready", profile };
  } catch {
    return { status: "error", message: "Unable to retrieve profile. Please try again." };
  }
}
