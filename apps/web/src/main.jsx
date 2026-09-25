import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';

import './index.css';
import { AuthProvider, useAuth } from './lib/useAuth';
import { Loading } from './components/ui';

import Landing from './pages/Landing';
import SignIn from './pages/SignIn';
import Dashboard from './pages/Dashboard';
import NewApp from './pages/NewApp';
import NewSite from './pages/NewSite';
import Builder from './pages/Builder';
import PublishedApp from './pages/runtime/PublishedApp';
import PublishedSite from './pages/PublishedSite';

/** Gate for the builder side. Published apps have their own separate sign-in. */
function RequireAuth({ children }) {
  const { user, checking } = useAuth();
  if (checking) return <Loading label="Signing you in…" />;
  if (!user) return <Navigate to="/signin" replace />;
  return children;
}

function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/signin" element={<SignIn />} />
      <Route path="/signup" element={<SignIn mode="signup" />} />

      <Route
        path="/dashboard"
        element={
          <RequireAuth>
            <Dashboard />
          </RequireAuth>
        }
      />
      <Route
        path="/new"
        element={
          <RequireAuth>
            <NewApp />
          </RequireAuth>
        }
      />
      <Route
        path="/new/site"
        element={<RequireAuth><NewSite /></RequireAuth>}
      />
      <Route
        path="/projects/:projectId/*"
        element={
          <RequireAuth>
            <Builder />
          </RequireAuth>
        }
      />

      {/* Published things. These are what a customer shares. */}
      <Route path="/a/:slug/*" element={<PublishedApp />} />
      <Route path="/s/:slug" element={<PublishedSite />} />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
