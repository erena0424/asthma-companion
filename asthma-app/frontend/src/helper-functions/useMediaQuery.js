import { useEffect, useState } from "react";

function useMediaQuery(query) {
    // set initial state as to whether current screen size matches requirement
    const [matches, setMatches] = useState(() =>
        window.matchMedia(query).matches
    );

    // watch out for screen size changing between meeting and not meeting requirements
    useEffect(() => {
        const media = window.matchMedia(query);

        const listener = () => setMatches(media.matches);
        media.addEventListener("change", listener);

        // when component unmounts, remove unused listener
        return () => media.removeEventListener("change", listener);
    }, [query]);

    return matches;
}

export default useMediaQuery;