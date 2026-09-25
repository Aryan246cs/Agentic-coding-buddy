import { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';

import { useAuth } from '../lib/useAuth';
import { Alert, Button, Field, Input, Loading } from '../components/ui';

export default function SignIn({ mode = 'login' }) {
  const { user, checking, signIn } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({ name: '', email: '', password: '' });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const isSignup = mode === 'signup';

  if (checking) return <Loading />;
  if (user) return <Navigate to="/dashboard" replace />;

  const update = (key) => (event) => setForm({ ...form, [key]: event.target.value });

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await signIn(
        isSignup ? form : { email: form.email, password: form.password },
        mode,
      );
      navigate('/dashboard');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app-shell flex min-h-screen items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm">
        <Link to="/" className="mb-8 flex items-center justify-center gap-2 text-lg font-semibold text-white">
          <span className="grid h-7 w-7 place-items-center rounded-lg bg-gradient-to-br from-violet-400 to-cyan-300 text-sm text-slate-950">S</span>Sequence
        </Link>

        <div className="rounded-2xl border border-white/10 bg-white/[.05] p-6 shadow-2xl shadow-black/30 backdrop-blur-sm">
          <h1 className="text-xl font-semibold text-white">
            {isSignup ? 'Create your account' : 'Welcome back'}
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            {isSignup
              ? 'Free to start. No card needed.'
              : 'Sign in to your apps and sites.'}
          </p>

          <form onSubmit={submit} className="mt-6 space-y-4">
            {error && <Alert>{error}</Alert>}

            {isSignup && (
              <Field label="Your name" required>
                <Input
                  value={form.name}
                  onChange={update('name')}
                  placeholder="Asha Rao"
                  autoComplete="name"
                  required
                />
              </Field>
            )}

            <Field label="Email" required>
              <Input
                type="email"
                value={form.email}
                onChange={update('email')}
                placeholder="you@yourbusiness.com"
                autoComplete="email"
                required
              />
            </Field>

            <Field
              label="Password"
              required
              hint={isSignup ? 'At least 8 characters.' : null}
            >
              <Input
                type="password"
                value={form.password}
                onChange={update('password')}
                autoComplete={isSignup ? 'new-password' : 'current-password'}
                required
              />
            </Field>

            <Button type="submit" size="lg" loading={busy} className="w-full">
              {isSignup ? 'Create account' : 'Sign in'}
            </Button>
          </form>
        </div>

        <p className="mt-4 text-center text-sm text-slate-400">
          {isSignup ? 'Already have an account? ' : "Don't have an account? "}
          <Link
            to={isSignup ? '/signin' : '/signup'}
            className="font-medium text-cyan-200 underline underline-offset-2"
          >
            {isSignup ? 'Sign in' : 'Sign up'}
          </Link>
        </p>
      </div>
    </div>
  );
}
