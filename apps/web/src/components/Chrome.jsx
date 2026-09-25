/** The signed-in frame: a top bar and a centred column. */

import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../lib/useAuth';

export default function Chrome({ children, wide = false }) {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="app-shell min-h-screen">
      <header className="border-b border-white/10 bg-[#0b0d13]/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link to="/dashboard" className="flex items-center gap-2 font-semibold tracking-tight text-white">
            <span className="grid h-7 w-7 place-items-center rounded-lg bg-gradient-to-br from-violet-400 to-cyan-300 text-sm text-slate-950">S</span>
            Sequence
          </Link>
          <div className="flex items-center gap-4">
            <span className="hidden text-sm text-slate-400 sm:inline">{user?.name}</span>
            <button
              onClick={() => {
                signOut();
                navigate('/');
              }}
              className="text-sm font-medium text-slate-400 transition hover:text-white"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className={`relative mx-auto px-6 py-10 ${wide ? 'max-w-6xl' : 'max-w-4xl'}`}>
        {children}
      </main>
    </div>
  );
}
