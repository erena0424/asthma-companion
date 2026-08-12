import { Container, Row, Col, Button } from "react-bootstrap";
import CancelButton from "../input/CancelButton";

function FormModal({
    title,
    children,
    onHide,
    onSubmit,
    submitText="Submit",
    buttonError="",
    buttonSuccess="",
    shake=false,
    showSubmit=true,
    color="dark"
}) {

    const colorClass = color === "light" ? "cream-body" : color === "green" ? "green-body" : "dark-green-body";
    const buttonClass = color === "light" ? "button-dark" : color === "green" ? "button-dark" : "button-light";

    return (
        <div className="form-modal-overlay">
            <Container
                className={`${colorClass} form-modal p-5 vertical-0 vertical-fill position-relative`}
            >
            {
                // x button will be placed in top-right corner absolutely (without affecting placement of other items)
                <CancelButton className={`${buttonClass} p-2 absolute-top-right`} onClick={onHide} />
            }
                <Row>
                    <Col className="form-modal-header">
                        <h2 className="text-center avoid-right">
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
                        <p className="error-text-light at-middle-center">
                            {buttonError}
                        </p>
                        <p className="at-middle-center">
                            {buttonSuccess}
                        </p>
                        <Button
                            className={`${buttonClass} btn-medium-text ${
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