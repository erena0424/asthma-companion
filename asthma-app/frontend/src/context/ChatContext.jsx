import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
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
    const requestVersion = useRef(0);
    const history = useRef([]);
    const contextToken = useRef(null);
    const sending = useRef(false);
    const currentToken = useRef(token);
    currentToken.current = token;

    const clearChat = useCallback(() => {
        requestVersion.current += 1;
        history.current = [];
        contextToken.current = null;
        sending.current = false;
        setIsSending(false);
        setMessages([INITIAL_MESSAGE]);
    }, []);

    useEffect(() => {
        clearChat();
        setPersona("warm");
        setIncludeSavedContext(false);
    }, [token, clearChat]);

    const changeSavedContext = useCallback((enabled) => {
        clearChat();
        setIncludeSavedContext(enabled);
    }, [clearChat]);

    const sendMessage = useCallback(async (message) => {
        const trimmed = message.trim();
        if (!trimmed || sending.current) return;
        if (!token) {
            setMessages(prev => [...prev, { id: crypto.randomUUID(), sender: "ai", text: "Please sign in to chat." }]);
            return;
        }
        const version = ++requestVersion.current;
        sending.current = true;
        setIsSending(true);
        setMessages(prev => [...prev, { id: crypto.randomUUID(), sender: "user", text: trimmed }]);
        const stillCurrent = () => version === requestVersion.current && token === currentToken.current;
        try {
            const data = await askCompanion({ token, message: trimmed, persona, includeSavedContext,
                history: history.current, contextToken: contextToken.current });
            if (!stillCurrent()) return;
            if (!data.history_accepted || data.generation_status !== "generated") history.current = [];
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

    return <ChatContext.Provider value={{ messages, isSending, sendMessage, clearChat,
        persona, setPersona, includeSavedContext, setIncludeSavedContext: changeSavedContext }}>
        {children}
    </ChatContext.Provider>;
}

export function useChat() {
    const context = useContext(ChatContext);
    if (!context) throw new Error("useChat must be used inside a ChatProvider");
    return context;
}
