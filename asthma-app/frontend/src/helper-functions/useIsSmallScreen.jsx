import { useEffect, useState } from "react";

function useIsSmallScreen() {
    const [isSmallScreen, setIsSmallScreen] = useState(
        () => window.matchMedia("(max-width: 767px)").matches
    );

    useEffect(() => {
        const mediaQuery = window.matchMedia("(max-width: 767px)");

        function handleChange(e) {
            setIsSmallScreen(e.matches);
        }

        mediaQuery.addEventListener("change", handleChange);

        return () => {
            mediaQuery.removeEventListener("change", handleChange);
        };
    }, []);

    return isSmallScreen;
}

export default useIsSmallScreen;