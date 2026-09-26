function Checkbox({
    checked,
    onChange,
    children,
    theme = "light",
    size = 32,
    strokeWidth = 4
}) {
    return (
        <label
            className={`checkbox ${theme}`}
            style={{
                "--checkbox-size": `${size}px`,
                "--check-stroke": strokeWidth
            }}
        >
            <input
                type="checkbox"
                checked={checked}
                onChange={(e) => onChange(e.target.checked)}
            />

            <span className="checkbox-box">
                {checked && (
                    <svg
                        width={size}
                        height={size}
                        viewBox="0 0 20 20"
                    >
                        <path
                            d="M4 10 L8 14 L16 6"
                            fill="none"
                            stroke="var(--checkbox-check)"
                            strokeWidth="var(--check-stroke)"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                        />
                    </svg>
                )}
            </span>

            <span className="checkbox-label">
                {children}
            </span>
        </label>
    );
}

export default Checkbox;