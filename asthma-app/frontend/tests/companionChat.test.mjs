// Temporary jsdom dependency: see docs/BUILDFEST_BACKEND_SETUP.md.
import assert from "node:assert/strict";
import { test } from "node:test";
import { createServer } from "vite";
import reactPlugin from "@vitejs/plugin-react";
const { JSDOM } = await import(process.env.JSDOM_MODULE || "jsdom");
const dom = new JSDOM("<!doctype html><div id='root'></div>", { url: "http://localhost" });
for (const key of ["window", "document", "HTMLElement", "HTMLTextAreaElement", "Event", "localStorage"]) globalThis[key] = dom.window[key];
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
dom.window.HTMLElement.prototype.scrollIntoView = () => {};
const { default: React, act } = await import("react");
const { createRoot } = await import("react-dom/client");
const server = await createServer({ configFile: false, envDir: false, plugins: [reactPlugin()],
    server: { middlewareMode: true, hmr: false, ws: false }, optimizeDeps: { noDiscovery: true, include: [] }, appType: "custom" });
try {
    const { ChatProvider, useChat } = await server.ssrLoadModule("/src/context/ChatContext.jsx");
    const { default: ChatContent } = await server.ssrLoadModule("/src/components/input/ChatContent.jsx");
    const { AuthProvider, useAuth } = await server.ssrLoadModule("/src/context/AuthContext.jsx");
    let chat, auth, request, resolvePending;
    let reply = { message: "A supportive reply", generation_status: "generated", context_token: "revision", history_accepted: true, forecast: { status: "unavailable", data: null } };
    let pending = false;
    globalThis.fetch = async (url, options) => {
        request = { url, body: JSON.parse(options.body) };
        if (pending) await new Promise(resolve => { resolvePending = resolve; });
        return { ok: true, json: async () => reply };
    };
    function Capture() { chat = useChat(); auth = useAuth(); return React.createElement(ChatContent); }
    localStorage.setItem("token", "e30.e30.demo");
    const root = createRoot(document.getElementById("root"));
    await act(async () => root.render(React.createElement(AuthProvider, null, React.createElement(ChatProvider, null, React.createElement(Capture)))));
    const click = async label => { const b = [...document.querySelectorAll("button")].find(b => b.textContent.trim() === label || b.getAttribute("aria-label") === label); assert.ok(b); await act(async () => b.click()); };
    await test("initial request excludes synthetic greeting and technical metadata", async () => {
        assert.equal(document.querySelector("select").value, "warm");
        assert.equal(document.querySelector('[type="checkbox"]').checked, false);
        await act(async () => chat.sendMessage("Hello"));
        assert.ok(request.url.endsWith("/v1/companion/chat"));
        assert.deepEqual(request.body, { message: "Hello", persona: "warm", include_saved_context: false, history: [], context_token: null });
        assert.ok(!document.querySelector('[role="log"]').textContent.includes("stored forecast"));
        assert.ok(!document.body.textContent.includes("Each message"));
    });
    await test("successful exchange is sent on follow-up, bounded to complete recent pairs", async () => {
        await act(async () => chat.sendMessage("And tomorrow?"));
        assert.deepEqual(request.body.history, [{ role: "user", content: "Hello" }, { role: "assistant", content: "A supportive reply" }]);
        assert.equal(request.body.context_token, "revision");
        for (let i=0; i<6; i++) await act(async () => chat.sendMessage(`Question ${i}`));
        assert.equal(request.body.history.length,8);
        assert.equal(request.body.history[0].role,"user");
    });
    await test("tone and explicit opt-in reset history; fallback has no technical metadata", async () => {
        await act(async () => {
            const select = document.querySelector("select"); select.value = "direct"; select.dispatchEvent(new Event("change", { bubbles: true }));
            document.querySelector('[type="checkbox"]').click();
        });
        reply = { message: "Please try again shortly.", generation_status: "fallback", forecast: { status: "stale", data: { forecast_for: "2026-01-01" } } };
        await act(async () => chat.sendMessage("Follow-up"));
        assert.deepEqual(request.body, { message: "Follow-up", persona: "direct", include_saved_context: true, history: [], context_token: null });
        assert.ok(!document.body.textContent.includes("predefined message"));
        assert.ok(!document.querySelector('[role="log"]').textContent.includes("stored forecast"));
    });
    await test("fallback exchange is not reused", async () => {
        reply = { message: "Ready again", generation_status: "generated", context_token: "new", history_accepted: false };
        await act(async () => chat.sendMessage("Try again"));
        assert.deepEqual(request.body.history, []);
        assert.equal(request.body.context_token, null);
    });
    await test("clear during pending request discards its late reply and unlocks controls", async () => {
        pending = true;
        let work;
        await act(async () => { work = chat.sendMessage("Pending"); });
        assert.ok(document.querySelector("fieldset").disabled);
        await click("Clear Chat");
        await act(async () => { resolvePending(); await work; });
        assert.equal(chat.messages.length, 1);
        assert.equal(chat.isSending, false);
        pending = false;
        await act(async () => chat.sendMessage("Fresh start"));
        assert.deepEqual(request.body.history, []);
        pending = true;
    });
    await test("account change clears messages and resets tone/context, excluding late response", async () => {
        let work;
        await act(async () => { work = chat.sendMessage("Old account"); });
        await act(async () => auth.storeToken("e30.e30.other"));
        await act(async () => { resolvePending(); await work; });
        assert.equal(chat.messages.length, 1);
        assert.equal(chat.persona, "warm");
        assert.equal(chat.includeSavedContext, false);
        assert.equal(localStorage.length, 1); // auth token only; no chat storage
    });
    await act(async () => root.unmount());
} finally { await server.close(); dom.window.close(); }
