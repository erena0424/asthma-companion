import { Button } from "react-bootstrap";

function CancelButton({ onClick, className = "", style = {}, width = "36", height = "36", ariaLabel = "cancel" }) {
  return (
    <Button
        className={`${className}`}
        style={style}
        onClick={onClick}
        aria-label={ariaLabel}
    >
        <svg
            style={{
            width: `clamp(${width * 2 / 3}px, 5vw, ${width}px)`,
            height: `clamp(${height * 2 / 3}px, 5vw, ${height}px)`,
            }}
            viewBox="0 0 16 16"
            fill="none"
        >
            <path
                d="
                    M 8 8
                    l 4 -4
                    M 8 8
                    l 4 4
                    M 8 8
                    l -4 4
                    M 8 8
                    l -4 -4
                "
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
            />
        </svg>
    </Button>
  );
}

export default CancelButton;