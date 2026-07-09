import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from "react";
import {
  clearSession,
  getStoredSession,
  loginAdmin,
  type AdminSession,
} from "../services/adminService";

interface AuthContextValue {
  session: AdminSession | null;
  isAuthenticated: boolean;
  login: (
    username: string,
    password: string,
  ) => Promise<boolean>;
  logout: () => void;
}

const AuthContext = createContext<
  AuthContextValue | undefined
>(undefined);

export function AuthProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [session, setSession] =
    useState<AdminSession | null>(
      () => getStoredSession(),
    );

  const login = useCallback(
    async (
      username: string,
      password: string,
    ) => {
      try {
        const authenticated =
          await loginAdmin(
            username,
            password,
          );

        setSession(authenticated);
        return true;
      } catch {
        return false;
      }
    },
    [],
  );

  const logout = useCallback(() => {
    clearSession();
    setSession(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        session,
        isAuthenticated: !!session,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error(
      "useAuth must be used within an AuthProvider",
    );
  }

  return context;
}
