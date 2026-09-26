import { useEffect, useRef, useState } from "react";
import { Form, Button } from "react-bootstrap";
import ArrowButton from "./ArrowButton";
import { useChat } from "../../context/ChatContext";

function ChatContent() {
    const {
        messages,
        isSending,
        sendMessage,
        clearChat
    } = useChat();

    const [input, setInput] = useState("");
    const messagesEndRef = useRef(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({
            behavior: "smooth",
        });
    }, [messages]);

    function handleSend() {
        const trimmed = input.trim();

        if (!trimmed || isSending) {
            return;
        }

        sendMessage(trimmed);
        setInput("");
    }

    function handleKeyDown(e) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    }

    return (
        <div className="chatbot">
            <div className="chatbot-conversation">
                {messages.map((message) => (
                    <div
                        key={message.id}
                        className={`chatbot-row ${message.sender}`}
                    >
                        <div
                            className={`chatbot-bubble ${message.sender}`}
                            style={{ whiteSpace: "pre-wrap" }}
                        >
                            {message.text}
                        </div>
                    </div>
                ))}

                <div ref={messagesEndRef} />
            </div>

            <div className="chatbot-input">
                <div
                    className="chatbot-input-field card-0 light-theme"
                    style={{ borderRadius: "8px" }}
                >
                    <Form.Control
                        style={{ borderRadius: "4px" }}
                        as="textarea"
                        rows={2}
                        placeholder={
                            isSending
                                ? "Copilot is thinking..."
                                : "Type a message..."
                        }
                        value={input}
                        disabled={isSending}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                    />
                </div>

                <ArrowButton
                    className="button-light p-2"
                    isSend
                    onClick={handleSend}
                />
            </div>

            <Button
                className="button-error-light btn-medium-text button-medium"
                onClick={() => clearChat()}

            >
                Clear Chat
            </Button>
        </ div>
    );
}

export default ChatContent;