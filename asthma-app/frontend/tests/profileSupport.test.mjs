// Run with JSDOM_MODULE pointing to a temporary jsdom installation; see setup docs.
import assert from "node:assert/strict";
import { test } from "node:test";
import { createServer } from "vite";
import reactPlugin from "@vitejs/plugin-react";

const { JSDOM } = await import(process.env.JSDOM_MODULE || "jsdom");
const dom = new JSDOM("<!doctype html><div id='root'></div>", { url: "http://localhost" });
for (const key of ["window", "document", "HTMLElement", "HTMLInputElement", "HTMLTextAreaElement", "Event", "MouseEvent", "localStorage"]) {
  globalThis[key] = dom.window[key];
}
globalThis.getComputedStyle = dom.window.getComputedStyle;
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const { default: React, act } = await import("react");
const { createRoot } = await import("react-dom/client");
const server = await createServer({
  configFile: false, envDir: false, plugins: [reactPlugin()],
  server: { middlewareMode: true, hmr: false, ws: false }, optimizeDeps: { noDiscovery: true, include: [] }, appType: "custom",
});
try {
  const { default: ProfilePage } = await server.ssrLoadModule("/src/components/pages/ProfilePage.jsx");
  const { AuthProvider, useAuth } = await server.ssrLoadModule("/src/context/AuthContext.jsx");
  let auth;
  function Capture() { auth = useAuth(); return React.createElement(ProfilePage); }
  const root = createRoot(document.getElementById("root"));
  const contact = { id: "demo", firstName: "Demo", lastName: "Contact", phone: "(202) 555-0100", email: "" };
  let profile = { name: "Demo", emergency_contacts: [contact], care_goal: "", accessibility_needs: "" };
  let requests = [];
  let pending;
  let mode = "success";
  globalThis.fetch = async (_url, options) => {
    if (!options.body) return { ok: true, json: async () => structuredClone(profile) };
    const updates = JSON.parse(options.body);
    requests.push(updates);
    if (mode === "pending") await new Promise(resolve => { pending = resolve; });
    if (mode === "failure") return { ok: false, json: async () => ({ detail: "Save rejected" }) };
    profile = { ...profile, ...updates };
    if (updates.care_goal) profile.care_goal = updates.care_goal.trim();
    return { ok: true, json: async () => structuredClone(profile) };
  };
  localStorage.setItem("token", "e30." + Buffer.from(JSON.stringify({ sub: "demo", exp: 9999999999 })).toString("base64url") + ".demo");
  await act(async () => root.render(React.createElement(AuthProvider, null, React.createElement(Capture))));
  await act(async () => auth.updateUser(profile));
  const buttons = () => [...document.querySelectorAll("button")];
  const button = label => buttons().find(b => b.textContent.trim() === label || b.getAttribute("aria-label") === label);
  const click = async label => { const b = button(label); assert.ok(b, label); await act(async () => b.click()); };
  const input = async (element, value) => {
    const proto = element.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    await act(async () => {
      Object.getOwnPropertyDescriptor(proto, "value").set.call(element, value);
      element.dispatchEvent(new Event("input", { bubbles: true }));
    });
  };

  await test("contact edit waits for canonical response; failed save keeps draft and allows retry", async () => {
    await click("Edit Emergency Contacts");
    await click("Edit");
    const first = document.querySelector('input[placeholder="Enter first name"]');
    await input(first, "Updated");
    mode = "pending";
    await click("Save Changes");
    assert.ok(button("Saving...").disabled);
    assert.equal(requests.length, 1);
    assert.ok(document.body.textContent.includes("Demo"));
    mode = "failure";
    await act(async () => pending());
    assert.ok(document.body.textContent.includes("Save rejected"));
    assert.equal(first.value, "Updated");
    assert.equal(auth.user.emergency_contacts[0].firstName, "Demo");
    mode = "success";
    await click("Save Changes");
    assert.equal(auth.user.emergency_contacts[0].firstName, "Updated");
    assert.equal(document.querySelector('input[placeholder="Enter first name"]'), null);
  });

  await test("failed deletion retains saved contact; retry clears canonical array", async () => {
    mode = "failure";
    await click("cancel");
    assert.ok(document.body.textContent.includes("Save rejected"));
    assert.equal(auth.user.emergency_contacts.length, 1);
    mode = "success";
    await click("cancel");
    assert.deepEqual(auth.user.emergency_contacts, []);
    assert.deepEqual(requests.at(-1), { emergency_contacts: [] });
    await click("Close editor");
  });

  await test("add contact sends one intentional update and displays returned data", async () => {
    await click("Edit Emergency Contacts");
    await click("Add Contact");
    await input(document.querySelector('input[placeholder="Enter first name"]'), "New");
    await input(document.querySelector('input[placeholder="(XXX) XXX-XXXX"]'), "2025550101");
    await click("Add");
    assert.equal(auth.user.emergency_contacts.length, 1);
    assert.equal(auth.user.emergency_contacts[0].firstName, "New");
    assert.ok(auth.user.emergency_contacts[0].id);
    await click("Close editor");
  });

  await test("support editor preserves failed draft, applies server result and supports clearing", async () => {
    await click("Edit personal support information");
    const areas = document.querySelectorAll("textarea");
    assert.equal(areas[0].maxLength, 1000);
    await input(areas[0], "  My goal  ");
    await input(areas[1], "Larger text");
    mode = "failure";
    await click("Save Changes");
    assert.equal(areas[0].value, "  My goal  ");
    assert.equal(auth.user.care_goal, "");
    mode = "success";
    await click("Save Changes");
    assert.equal(auth.user.care_goal, "My goal");
    assert.equal(auth.user.accessibility_needs, "Larger text");
    await click("Edit personal support information");
    for (const area of document.querySelectorAll("textarea")) await input(area, "");
    await click("Save Changes");
    assert.equal(auth.user.care_goal, "");
    assert.equal(auth.user.accessibility_needs, "");
  });
  await test("a remounted session retrieves canonical saved profile through existing GET", async () => {
    await act(async () => root.render(null));
    await act(async () => root.render(React.createElement(AuthProvider, null, React.createElement(Capture))));
    await act(async () => auth.refreshUserProfile());
    assert.equal(auth.user.emergency_contacts[0].firstName, "New");
    assert.equal(auth.user.care_goal, "");
    assert.ok(document.body.textContent.includes("New"));
  });
  await act(async () => root.unmount());
} finally {
  await server.close();
  dom.window.close();
}
