/** Who is signed in to the platform, held in one place. */

import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { api, platformToken } from './api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    if (!platformToken.get()) {
      setChecking(false);
      return;
    }
    // A stored token can be expired or from an older signing key, so confirm
    // it with the server rather than trusting that it exists.
    api
      .me()
      .then(setUser)
      .catch(() => platformToken.clear())
      .finally(() => setChecking(false));
  }, []);

  const signIn = useCallback(async (credentials, mode = 'login') => {
    const result = mode === 'signup' ? await api.signup(credentials) : await api.login(credentials);
    platformToken.set(result.token);
    setUser(result.user);
    return result.user;
  }, []);

  const signOut = useCallback(() => {
    platformToken.clear();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, checking, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside an AuthProvider');
  return value;
}
