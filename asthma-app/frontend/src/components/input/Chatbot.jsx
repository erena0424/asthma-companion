import { useRef, useState, useLayoutEffect } from "react";
import { createPortal } from "react-dom";
import { Container, Row, Col } from "react-bootstrap";
import ToggleButton from "./ToggleButton";
import { Rnd } from "react-rnd";
import ChatContent from "./ChatContent";

function Chatbot({
    title = "Chat",
    beginClosed = false,
}) {
    const containerRef = useRef(null);

    const EXPANDED_DEFAULT = {
        width: 400,
        height: 500,
    };

    const [isCollapsed, setIsCollapsed] =
        useState(beginClosed);

    const [size, setSize] =
        useState(EXPANDED_DEFAULT);

    const previousExpandedSize = useRef(
        EXPANDED_DEFAULT
    );

    const [position, setPosition] = useState(() => ({
        x:
            window.innerWidth -
            EXPANDED_DEFAULT.width -
            20,
        y:
            window.innerHeight -
            EXPANDED_DEFAULT.height -
            20,
    }));

    useLayoutEffect(() => {
        if (isCollapsed && containerRef.current) {
            const { width, height } =
                containerRef.current.getBoundingClientRect();

            setSize({
                width: Math.ceil(width),
                height: Math.ceil(height),
            });
        } else {
            setSize(previousExpandedSize.current);
        }
    }, [isCollapsed, title]);

    function onCollapse() {
        setIsCollapsed((collapsed) => !collapsed);
    }

    const chatbot = (
        <div className="chatbot-layer">
            <Rnd
                size={size}
                position={position}
                onDragStop={(e, d) => {
                    setPosition({
                        x: d.x,
                        y: d.y,
                    });
                }}
                onResizeStop={(
                    e,
                    direction,
                    ref,
                    delta,
                    newPosition
                ) => {
                    const newSize = {
                        width: ref.offsetWidth,
                        height: ref.offsetHeight,
                    };

                    setSize(newSize);
                    previousExpandedSize.current = newSize;
                    setPosition(newPosition);
                }}
                enableResizing={
                    isCollapsed
                        ? {
                            left: true,
                            right: true,
                            top: false,
                            bottom: false,
                            topLeft: false,
                            topRight: false,
                            bottomLeft: false,
                            bottomRight: false,
                        }
                        : true
                }
                minWidth={300}
                minHeight={isCollapsed ? 0 : 300}
                bounds="parent"
                dragHandleClassName="chatbot-header"
                style={{
                    position: "fixed",
                    zIndex: 9999,
                }}
            >
                <Container
                    ref={containerRef}
                    className="contact-card d-flex flex-column chatbot-floating"
                    style={{
                        width: isCollapsed ? "auto" : "100%",
                        height: isCollapsed ? "auto" : "100%",
                        resize: "none",
                    }}
                >
                    {/* Floating chatbot header */}
                    <Row
                        className="vertical chatbot-header"
                        style={{
                            cursor: "move",
                            userSelect: "none",
                        }}
                    >
                        <Col className="position-relative">
                            <h2
                                className="text-center"
                                style={{
                                    overflowWrap: "break-word",
                                }}
                            >
                                {title}
                            </h2>

                            <div className="chatbot-collapse">
                                <ToggleButton
                                    className="button-light p-2"
                                    width="25"
                                    height="25"
                                    isCollapse={isCollapsed}
                                    onClick={onCollapse}
                                />
                            </div>
                        </Col>

                        {!isCollapsed && (
                            <Col>
                                <hr />
                            </Col>
                        )}
                    </Row>

                    {!isCollapsed && <ChatContent />}
                </Container>
            </Rnd>
        </div>
    );

    return createPortal(
        chatbot,
        document.body
    );
}

export default Chatbot;