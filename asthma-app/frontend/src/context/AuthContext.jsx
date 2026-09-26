import { createContext, useContext, useState, useEffect, useCallback, useRef } from "react";
import { getProfile, isJwt } from "../helper-functions/authentication";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    // get token, if it exists
    const [token, setToken] = useState(() => localStorage.getItem("token"));
    const [user, setUser] = useState(null);
    const [profileLoading, setProfileLoading] = useState(false);
    const [profileError, setProfileError] = useState("");
    const profileRequest = useRef(0);
    // setup complete or not
    const [setupComplete, setSetupComplete] = useState(() => {
        return localStorage.getItem("setupComplete") === "true";
    });

    // extracts user info
    function decodeJwt(token) {
        try {
            const payload = token.split(".")[1];
            return JSON.parse(atob(payload));
        } catch {
            return null;
        }
    }

    // whenever token changes, update the user
    useEffect(() => {
        if (!token) {
            setUser(null);
            return;
        }
        setUser(decodeJwt(token));
    }, [token]);

    // call whenever get new result from API
    function updateUser(updatedFields) {
        setUser(prev => ({
            ...prev,
            ...updatedFields,
        }));
    }

    // Ignore responses invalidated by a newer refresh or logout.
    const refreshUserProfile = useCallback(async () => {
        if (!isJwt(token)) return;
        const request = ++profileRequest.current;
        setProfileLoading(true);
        setProfileError("");
        const result = await getProfile(token);
        if (request !== profileRequest.current) return;
        setProfileLoading(false);
        if (result.status === "unauthorized") {
            logout();
        } else if (result.status === "error") {
            setProfileError(result.message);
        } else {
            setUser(result.profile);
        }
    }, [token]);

    // stores token in React and localStorage
    function storeToken(jwt) {
        profileRequest.current += 1;
        setProfileLoading(false);
        setProfileError("");
        localStorage.setItem("token", jwt);
        setToken(jwt);
    }

    // clears all user data
    function logout() {
        profileRequest.current += 1;
        setProfileLoading(false);
        setProfileError("");
        localStorage.removeItem("token");
        localStorage.removeItem("setupComplete");
        setToken(null);
        setUser(null);
        setSetupComplete(false);
    }

    // updates whether user's account has been setup
    function setSetupCompletePersisted(value) {
        localStorage.setItem("setupComplete", value ? "true" : "false");
        setSetupComplete(value);
    }

    return (
        <AuthContext.Provider value={{
            token,
            user,
            profileLoading,
            profileError,
            updateUser,
            refreshUserProfile,
            storeToken,
            logout,
            setupComplete,
            setSetupComplete: setSetupCompletePersisted
        }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
  return useContext(AuthContext);
}
