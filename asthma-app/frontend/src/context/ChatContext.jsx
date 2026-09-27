import { createContext, useCallback, useContext, useLayoutEffect, useRef, useState } from "react";
import { useAuth } from "./AuthContext";
import { askCompanion, boundedHistory } from "../helper-functions/askCompanion";

const ChatContext = createContext(null);
const INITIAL_MESSAGE = {
    id: "initial", sender: "ai",
    text: "Hello! What's on your mind today?",
};

export function ChatProvider({ children }) {
    const { token } = useAuth();
    const [messages, setMessages] = useState([INITIAL_MESSAGE]);
    const [isSending, setIsSending] = useState(false);
    const [persona, setPersona] = useState("warm");
    const [includeSavedContext, setIncludeSavedContext] = useState(false);
    const [openingFailed, setOpeningFailed] = useState(false);
    const openingAttempted = useRef(false);
    const openingMessage = useRef(null);
    const requestVersion = useRef(0);
    const history = useRef([]);
    const contextToken = useRef(null);
    const sending = useRef(false);
    const currentToken = useRef(token);
    const initializedToken = useRef(token);
    currentToken.current = token;

    const clearChat = useCallback(() => {
        requestVersion.current += 1;
        openingAttempted.current = true;
        openingMessage.current = null;
        setOpeningFailed(false);
        history.current = [];
        contextToken.current = null;
        sending.current = false;
        setIsSending(false);
        setMessages([INITIAL_MESSAGE]);
    }, []);

    useLayoutEffect(() => {
        if (initializedToken.current === token) return;
        initializedToken.current = token;
        clearChat();
        openingAttempted.current = false;
        setPersona("warm");
        setIncludeSavedContext(false);
    }, [token, clearChat]);

    const changeSavedContext = useCallback((enabled) => {
        clearChat();
        setIncludeSavedContext(enabled);
    }, [clearChat]);

    const openConversation = useCallback(async (retry = false) => {
        if (!token || sending.current || (openingAttempted.current && !retry)) return;
        openingAttempted.current = true;
        const version = ++requestVersion.current;
        sending.current = true;
        setIsSending(true);
        setOpeningFailed(false);
        const stillCurrent = () => version === requestVersion.current && token === currentToken.current;
        try {
            const data = await askCompanion({ token, persona, includeSavedContext, opening: true });
            if (!stillCurrent()) return;
            const generated = data.generation_status === "generated";
            openingMessage.current = generated ? data.message : null;
            contextToken.current = generated ? data.context_token : null;
            setMessages([{ id: "initial", sender: "ai", text: data.message }]);
            setOpeningFailed(!generated);
        } catch {
            if (stillCurrent()) {
                setMessages([INITIAL_MESSAGE]);
                setOpeningFailed(true);
            }
        } finally {
            if (stillCurrent()) {
                sending.current = false;
                setIsSending(false);
            }
        }
    }, [token, persona, includeSavedContext]);

    const sendMessage = useCallback(async (message) => {
        const trimmed = message.trim();
        if (!trimmed || sending.current) return;
        if (!token) {
            setMessages(prev => [...prev, { id: crypto.randomUUID(), sender: "ai", text: "Please sign in to chat." }]);
            return;
        }
        openingAttempted.current = true;
        setOpeningFailed(false);
        const version = ++requestVersion.current;
        sending.current = true;
        setIsSending(true);
        setMessages(prev => [...prev, { id: crypto.randomUUID(), sender: "user", text: trimmed }]);
        const stillCurrent = () => version === requestVersion.current && token === currentToken.current;
        try {
            const data = await askCompanion({ token, message: trimmed, persona, includeSavedContext,
                history: history.current, contextToken: contextToken.current, openingMessage: openingMessage.current });
            if (!stillCurrent()) return;
            if (!data.history_accepted || data.generation_status !== "generated") {
                history.current = [];
                openingMessage.current = null;
            }
            contextToken.current = data.context_token || null;
            if (data.generation_status === "generated") history.current = boundedHistory([
                ...history.current, { role: "user", content: trimmed },
                { role: "assistant", content: data.message },
            ]);
            setMessages(prev => [...prev, {
                id: crypto.randomUUID(), sender: "ai", text: data.message,
            }]);
        } catch (error) {
            if (!stillCurrent()) return;
            setMessages(prev => [...prev, {
                id: crypto.randomUUID(), sender: "ai",
                text: error.status === 401 ? "Your session has expired. Please sign in again." : error.message,
            }]);
        } finally {
            if (stillCurrent()) {
                sending.current = false;
                setIsSending(false);
            }
        }
    }, [token, persona, includeSavedContext]);

    return <ChatContext.Provider value={{ messages, isSending, sendMessage, clearChat, openConversation, openingFailed,
        persona, setPersona, includeSavedContext, setIncludeSavedContext: changeSavedContext }}>
        {children}
    </ChatContext.Provider>;
}

export function useChat() {
    const context = useContext(ChatContext);
    if (!context) throw new Error("useChat must be used inside a ChatProvider");
    return context;
}
