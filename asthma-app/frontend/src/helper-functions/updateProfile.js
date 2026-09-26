import { API_URL } from "../config"

export async function updateProfile(data, token) {
    const response = await fetch(`${API_URL}/v1/users/me`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(data),
    });

    if (!response.ok) {
        throw new Error("Unable to save profile.");
    }

    return response.json();
}