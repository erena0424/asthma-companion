import { Container, Row, Col } from "react-bootstrap";
import EditButton from "../input/EditButton";
import CancelButton from "../input/CancelButton";

function ContactCard({
    contact,
    onEdit,
    onDelete
}) {

    return (
        <Container className="contact-card position-relative">
            <Row className="vertical">
                <Col className="horizontal-16">
                    <div
                        style={{ minWidth: 0, flexShrink: 1, overflowWrap: "break-word" }}
                    >{contact.firstName}</div>
                    <div
                        style={{ minWidth: 0, flexShrink: 1, overflowWrap: "break-word" }}
                    >{contact.lastName}</div>
                    <div style={{ flexGrow: 1 }} />
               

                    <div className="horizontal-8" style={{ flexShrink: 0, alignSelf: "flex-start" }}>
                        <EditButton
                            className="button-light button-small"
                            width="25"
                            height="25"
                            onClick={onEdit}
                        />

                        <CancelButton
                            className="button-light button-small"
                            width="25"
                            height="25"
                            onClick={onDelete}
                        />
                    </div>
                </Col>

                <Col
                    className="horizontal-16"
                    style={{
                        justifyContent: "space-between"
                    }}
                >
                    <div>{contact.phone}</div>
                    <div
                        style={{ minWidth: 0, flexShrink: 1, overflowWrap: "break-word" }}
                    >{contact.email}</div>
                </Col>
            </Row>
        </Container>
    );
}

export default ContactCard;