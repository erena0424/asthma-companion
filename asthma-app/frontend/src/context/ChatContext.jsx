import {
    createContext,
    useCallback,
    useContext,
    useEffect,
    useState,
} from "react";
import { useAuth } from "./AuthContext";
import {
    askCopilot,
    formatCopilotReply,
} from "../helper-functions/askCopilot";

const ChatContext = createContext(null);

const INITIAL_MESSAGE = {
    id: "initial",
    sender: "ai",
    text:
        "Hello! Ask about today's risk, pollen, or plans. " +
        "For symptoms and inhaler use, log a check-in so they count toward your prediction.",
};

export function ChatProvider({ children }) {
    const { token } = useAuth();

    const [messages, setMessages] = useState([INITIAL_MESSAGE]);
    const [isSending, setIsSending] = useState(false);

    const clearChat = useCallback(() => {
        setMessages([INITIAL_MESSAGE]);
    }, []);

    const sendMessage = useCallback(
        async (message) => {
            const trimmed = message.trim();

            if (!trimmed || isSending) {
                return;
            }

            if (!token) {
                setMessages((prev) => [
                    ...prev,
                    {
                        id: Date.now(),
                        sender: "ai",
                        text: "Please log in to chat with Copilot.",
                    },
                ]);
                return;
            }

            const userMessage = {
                id: Date.now(),
                sender: "user",
                text: trimmed,
            };

            setMessages((prev) => [...prev, userMessage]);
            setIsSending(true);

            try {
                const data = await askCopilot({
                    token,
                    message: trimmed,
                });

                const reply = formatCopilotReply(data.advice);

                setMessages((prev) => [
                    ...prev,
                    {
                        id: Date.now() + 1,
                        sender: "ai",
                        text: reply,
                    },
                ]);
            } catch (error) {
                let text =
                    error.message ||
                    "Unable to reach Copilot right now.";

                if (
                    error.code === "FORECAST_NOT_FOUND" ||
                    error.status === 404
                ) {
                    text =
                        "No prediction is available yet. Complete today's " +
                        "check-in and generate a forecast on Home or Statistics first.";
                }

                setMessages((prev) => [
                    ...prev,
                    {
                        id: Date.now() + 1,
                        sender: "ai",
                        text,
                    },
                ]);
            } finally {
                setIsSending(false);
            }
        },
        [token, isSending]
    );

    return (
        <ChatContext.Provider
            value={{
                messages,
                isSending,
                sendMessage,
                clearChat,
            }}
        >
            {children}
        </ChatContext.Provider>
    );
}

export function useChat() {
    const context = useContext(ChatContext);

    if (!context) {
        throw new Error(
            "useChat must be used inside a ChatProvider"
        );
    }

    return context;
}