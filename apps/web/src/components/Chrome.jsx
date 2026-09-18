/** The signed-in frame: a top bar and a centred column. */

import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../lib/useAuth';

export default function Chrome({ children, wide = false }) {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <Link to="/dashboard" className="font-semibold tracking-tight text-slate-900">
            Sequence
          </Link>
          <div className="flex items-center gap-4">
            <span className="hidden text-sm text-slate-600 sm:inline">{user?.name}</span>
            <button
              onClick={() => {
                signOut();
                navigate('/');
              }}
              className="text-sm font-medium text-slate-600 hover:text-slate-900"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className={`mx-auto px-6 py-8 ${wide ? 'max-w-6xl' : 'max-w-4xl'}`}>
        {children}
      </main>
    </div>
  );
}
