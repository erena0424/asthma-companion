import { Button } from "react-bootstrap";

function ArrowButton({ isBack=false, isSend=false, size = 48, onClick, className = "", style = {}, width = "36", height = "36" }) {
  return (
    <Button
        className={`${className}`}
        style={style}
        onClick={onClick}
        aria-label={isSend ? "send" : isBack ? "back" : "next"}
    >
        <svg className={`${!isBack ? "rotate-180" : ""} ${isSend ? "rotate-90" : ""}`}  width={width} height={height} viewBox="0 0 16 16" fill="none">
        <path
            d="
                M 14 8
                H 3
                l 4 -4
                M 3 8
                l 4 4
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

export default ArrowButton;