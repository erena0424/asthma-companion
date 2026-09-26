import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { getProfile } from "../helper-functions/authentication";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    // get token, if it exists
    const [token, setToken] = useState(() => localStorage.getItem("token"));
    const [user, setUser] = useState(null);
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

    // call whenever need to get current user data from API
    const refreshUserProfile = useCallback(async () => {
        if (!token) return;

        const result = await getProfile(token);

        if (typeof result === "string") {
            console.error(result);
            return;
        }

        setUser(result);
    }, [token]);

    // stores token in React and localStorage
    function storeToken(jwt) {
        localStorage.setItem("token", jwt);
        setToken(jwt);
    }

    // clears all user data
    function logout() {
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
