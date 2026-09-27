import { useEffect, useRef, useState } from "react";
import { Form, Button } from "react-bootstrap";
import ArrowButton from "./ArrowButton";
import { useChat } from "../../context/ChatContext";

function ChatContent() {
    const {
        messages,
        isSending,
        sendMessage,
        openConversation, openingFailed, clearChat, persona, setPersona, includeSavedContext, setIncludeSavedContext
    } = useChat();

    useEffect(() => { openConversation(); }, [openConversation]);

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
            <fieldset disabled={isSending} style={{ border: 0, padding: 0 }}>
                <label className="d-block">
                    Reply tone
                    <Form.Select value={persona} onChange={e => setPersona(e.target.value)}>
                        <option value="warm">Warm</option>
                        <option value="calm">Calm</option>
                        <option value="direct">Direct</option>
                    </Form.Select>
                </label>
                <label className="d-block mt-2">
                    <input type="checkbox" checked={includeSavedContext}
                        onChange={e => setIncludeSavedContext(e.target.checked)} />{" "}
                    Include my saved context
                </label>
                <small className="d-block">
                    When checked, your care goal, accessibility needs, saved triggers,
                    environment preference and approved summary are sent to the AI provider.
                    A stored forecast may be included either way.
                </small>
            </fieldset>
            <div className="chatbot-conversation" role="log" aria-label="Companion conversation">
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

            {openingFailed && <Button disabled={isSending} onClick={() => openConversation(true)}>Try greeting again</Button>}

            <div className="chatbot-input">
                <div
                    className="chatbot-input-field card-0 light-theme"
                    style={{ borderRadius: "8px" }}
                >
                    <Form.Control
                        style={{ borderRadius: "4px" }}
                        as="textarea"
                        rows={2}
                        maxLength={1000}
                        aria-label="Message to companion"
                        placeholder={
                            isSending
                                ? "Companion is replying..."
                                : "Type a message..."
                        }
                        value={input}
                        disabled={isSending}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                    />
                </div>

                <fieldset disabled={isSending || !input.trim()} style={{ border: 0, padding: 0 }}>
                <ArrowButton
                    className="button-light p-2"
                    isSend
                    onClick={handleSend}
                />
                </fieldset>
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