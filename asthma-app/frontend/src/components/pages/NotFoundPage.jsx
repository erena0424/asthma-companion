import { Button } from "react-bootstrap";
import { useNavigate } from "react-router";

export function NotFoundPage() {
    const navigate = useNavigate();

    return (
        <div className="vertical-48 at-top-center p-5">
        <h1>Page Not Found</h1>
        <h2>The URL you used is invalid.</h2>

        <Button
            className="button-dark btn-large-text"
            onClick={() => {
                // navigate to previous page, if it exists
                if (window.history.length > 1) {
                    navigate(-1);
                }
                // otherwise navigate to home
                else {
                    navigate("/", { replace: true });
                }
            }}
        >
            Return
        </Button>
        </div>
    );
}

export default NotFoundPage;