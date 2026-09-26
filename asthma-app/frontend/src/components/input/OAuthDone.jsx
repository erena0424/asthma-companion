import { useEffect } from "react";

export default function OAuthDone() {
  useEffect(() => {
    if (window.opener) {
      window.opener.postMessage({ type: "google-calendar-connected" }, "*");
    }
    window.close();
  }, []);

  return (
    <main style={{ padding: "2rem", textAlign: "center" }}>
      <h2>Google Calendar connected</h2>
      <p>You can close this tab.</p>
    </main>
  );
}