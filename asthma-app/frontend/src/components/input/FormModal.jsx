import { Container, Row, Col, Button } from "react-bootstrap";
import CancelButton from "../input/CancelButton";

function FormModal({
    title,
    children,
    onHide,
    onSubmit,
    submitText="Submit",
    buttonError="",
    shake=false,
    showSubmit=true
}) {

    return (
        <div className="form-modal-overlay">
            <Container
                className="dark-green-body form-modal p-5 vertical-32 vertical-fill position-relative"
            >
            {
                // x button will be placed in top-right corner absolutely (without affecting placement of other items)
                <CancelButton className="button-light p-2 absolute-top-right" onClick={onHide} />
            }
                <Row>
                    <Col className="form-modal-header">
                        <h2 className="text-center">
                            {title}
                        </h2>
                        <hr />
                    </Col>
                </Row>

                <Row className="scrollable flex-grow-1" style={{minHeight:"50px"}}>
                    {children}
                </Row>

                {showSubmit && (
                    <Row className="vertical-16 form-modal-footer flex-shrink-0">
                        <div className="error-text-light at-middle-center">
                            {buttonError}
                        </div>
                        <Button
                            className={`button-light btn-medium-text ${
                                shake ? "shake" : ""
                            }`}
                            onClick={onSubmit}
                        >
                            {submitText}
                        </Button>
                    </Row>
                )}

            </Container>

        </div>
    );
}

export default FormModal;