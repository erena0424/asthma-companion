import { Button } from "react-bootstrap";

function EditButton({ onClick, className = "", style = {}, width = "36", height = "36", ariaLabel = "" }) {
    return (
        <Button
            className={className}
            style={style}
            onClick={onClick}
            aria-label={`${ariaLabel ? ariaLabel : "Edit"}`}
        >
            <svg
                width={width}
                height={height}
                viewBox="0 0 36 36"
                fill="currentColor"
            >
                {/* Page */}
                <path d="
                    M10 4
                    H15
                    C16.9 4.3 16.9 6.7 15 7
                    V7
                    H10
                    C8.4 7 7 8.4 7 10
                    V26
                    C7 27.6 8.4 29 10 29
                    H26
                    C27.6 29 29 27.6 29 26
                    V20
                    C29 19.2 29.7 18.5 30.5 18.5
                    C31.3 18.5 32 19.2 32 20
                    V26
                    C32 29.3 29.3 32 26 32
                    H10
                    C6.7 32 4 29.3 4 26
                    V10
                    C4 6.7 6.7 4 10 4
                    Z
                " />

                {/* Pencil (single shape) */}
                <path d="
                    M23.8 6.2
                    L29.8 12.2
                    L18.2 23.8
                    H12.6
                    V18.2
                    Z

                    M24.9 5.1
                    L26.9 3.1
                    C27.6 2.4 28.8 2.4 29.5 3.1
                    L32.9 6.5
                    C33.6 7.2 33.6 8.4 32.9 9.1
                    L30.9 11.1
                    Z
                " />
            </svg>
        </Button>
    );
}

export default EditButton;