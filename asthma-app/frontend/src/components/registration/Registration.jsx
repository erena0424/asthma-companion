import { Container, Row, Col } from 'react-bootstrap';
import ArrowButton from '../input/ArrowButton';
import SegmentedProgressBar from '../input/SegmentedProgressBar';
import { Spinner } from "react-bootstrap";

export function Registration({
  numPage = 0,
  numPages = 7,
  onNext,
  onBack,
  nextDisabled,
  buttonError,
  shake,
  saving,
  children
}) {

    let headerEle = <></>;

    // first page
    if (numPage === 0) {
        headerEle = <h1>Welcome!</h1>;
    }
    // last page
    else if (numPage === numPages - 1) {
        headerEle = <h1>Thank You!</h1>;
    }
    // other
    else {
        headerEle = (
            <SegmentedProgressBar
                numPage={numPage - 1}
                numPages={numPages - 2}
            />
        );
    }

    return (
        <Container
            fluid
            className="registration-container"
        >
            <div className="registration-content">

                {/* fixed header */}
                <div className="registration-header">
                    {headerEle}
                    <hr />
                </div>

                {/* scrollable middle */}
                <div className="registration-body">
                    {children}
                </div>

                {/* fixed footer */}
                <div className="registration-footer">

                    <p className="error-text-dark">
                        {buttonError}
                    </p>

                    <div
                        className="horizontal-48 at-bottom-center"
                        style={{
                                display: "flex",
                                justifyContent: "center",
                                alignItems: "center"
                            }}
                    >

                        {
                            numPage !== 0 && numPage !== numPages - 1 &&
                            <ArrowButton
                                className="button-dark btn-arrow"
                                isBack={true}
                                onClick={onBack}
                            />
                        }

                        {
                            saving ? (
                                <Spinner
                                    animation="border"
                                    role="status"
                                    style={{
                                        width: "48px",
                                        height: "48px",
                                        color: "var(--color-secondary)",
                                    }}
                                />
                            ) : (
                                <ArrowButton
                                    className={`button-dark btn-arrow ${shake ? "shake" : ""}`}
                                    isBack={false}
                                    onClick={onNext}
                                    disabled={nextDisabled}
                                />
                            )
                        }

                    </div>
                </div>
            </div>
        </Container>
    );
}

export default Registration;