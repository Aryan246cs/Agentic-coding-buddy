/**
 * The small set of pieces every screen is built from.
 *
 * Kept deliberately plain. The product's job is to make a non-technical person
 * feel in control, and that comes from clear words and generous spacing far
 * more than from decoration.
 */

import { Link } from 'react-router-dom';

const cx = (...parts) => parts.filter(Boolean).join(' ');

const VARIANTS = {
  primary: 'bg-gradient-to-r from-violet-500 to-indigo-500 text-white shadow-lg shadow-violet-950/40 hover:from-violet-400 hover:to-indigo-400 disabled:bg-slate-700',
  secondary:
    'border border-white/10 bg-white/[0.05] text-slate-200 hover:border-white/20 hover:bg-white/[0.09] disabled:text-slate-500',
  danger: 'border border-red-400/30 bg-red-500/10 text-red-300 hover:bg-red-500/20',
  approve: 'bg-emerald-500 text-white hover:bg-emerald-400 disabled:bg-emerald-950',
  reject: 'border border-red-400/30 bg-red-500/10 text-red-300 hover:bg-red-500/20',
  ghost: 'text-slate-400 hover:bg-white/[0.06] hover:text-white',
};

const SIZES = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-sm',
  lg: 'px-5 py-2.5 text-base',
};

export function Button({
  variant = 'primary',
  size = 'md',
  className,
  loading = false,
  children,
  ...props
}) {
  return (
    <button
      className={cx(
        'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors',
        'focus:outline-none focus:ring-2 focus:ring-violet-400 focus:ring-offset-2 focus:ring-offset-[#0b0d13]',
        'disabled:cursor-not-allowed',
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
      disabled={loading || props.disabled}
      {...props}
    >
      {loading && <Spinner className="h-4 w-4" />}
      {children}
    </button>
  );
}

export function LinkButton({ to, variant = 'primary', size = 'md', className, children }) {
  return (
    <Link
      to={to}
      className={cx(
        'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors',
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
    >
      {children}
    </Link>
  );
}

export function Spinner({ className = 'h-5 w-5' }) {
  return (
    <svg className={cx('animate-spin', className)} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity="0.25" />
      <path
        d="M12 2a10 10 0 0 1 10 10"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function Card({ className, children, ...props }) {
  return (
    <div
      className={cx('rounded-2xl border border-white/[0.10] bg-white/[0.045] shadow-2xl shadow-black/10 backdrop-blur-sm', className)}
      {...props}
    >
      {children}
    </div>
  );
}

const TONES = {
  neutral: 'bg-white/[0.08] text-slate-300',
  good: 'bg-emerald-400/10 text-emerald-300 ring-1 ring-emerald-400/20',
  bad: 'bg-red-400/10 text-red-300 ring-1 ring-red-400/20',
  waiting: 'bg-amber-400/10 text-amber-200 ring-1 ring-amber-400/20',
  info: 'bg-cyan-400/10 text-cyan-200 ring-1 ring-cyan-400/20',
};

export function Badge({ tone = 'neutral', className, children }) {
  return (
    <span
      className={cx(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

/** Maps a status word to a colour, so every screen reads the same way. */
export function StatusBadge({ status }) {
  const value = String(status || '').toLowerCase();
  const tone =
    ['approved', 'completed', 'ok', 'resolved', 'published'].includes(value)
      ? 'good'
      : ['rejected', 'failed'].includes(value)
        ? 'bad'
        : ['pending', 'waiting_approval', 'waiting', 'new', 'escalated', 'draft'].includes(value)
          ? 'waiting'
          : 'neutral';

  const label = value.replace(/_/g, ' ');
  return <Badge tone={tone}>{label.charAt(0).toUpperCase() + label.slice(1)}</Badge>;
}

export function Field({ label, hint, error, required, children }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-slate-200">
        {label}
        {required && <span className="ml-0.5 text-red-500">*</span>}
      </span>
      {children}
      {hint && !error && <span className="mt-1 block text-xs text-slate-500">{hint}</span>}
      {error && <span className="mt-1 block text-xs text-red-600">{error}</span>}
    </label>
  );
}

export const inputClass =
  'w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white ' +
  'placeholder:text-slate-500 focus:border-violet-400/70 focus:outline-none focus:ring-1 ' +
  'focus:ring-violet-400/50 disabled:bg-white/[0.03]';

export function Input({ className, ...props }) {
  return <input className={cx(inputClass, className)} {...props} />;
}

export function Textarea({ className, rows = 4, ...props }) {
  return <textarea rows={rows} className={cx(inputClass, 'resize-y', className)} {...props} />;
}

export function Select({ className, children, ...props }) {
  return (
    <select className={cx(inputClass, 'bg-[#151823]', className)} {...props}>
      {children}
    </select>
  );
}

export function Alert({ tone = 'bad', title, children, onDismiss }) {
  const styles = {
    bad: 'border-red-400/30 bg-red-500/10 text-red-200',
    good: 'border-emerald-400/30 bg-emerald-500/10 text-emerald-200',
    warn: 'border-amber-400/30 bg-amber-500/10 text-amber-100',
    info: 'border-cyan-400/30 bg-cyan-500/10 text-cyan-100',
  };
  return (
    <div className={cx('rounded-lg border px-4 py-3 text-sm', styles[tone])}>
      <div className="flex items-start justify-between gap-3">
        <div>
          {title && <p className="font-semibold">{title}</p>}
          <div className={title ? 'mt-1' : ''}>{children}</div>
        </div>
        {onDismiss && (
          <button onClick={onDismiss} className="shrink-0 opacity-60 hover:opacity-100">
            ✕
          </button>
        )}
      </div>
    </div>
  );
}

export function EmptyState({ title, children, action }) {
  return (
    <div className="rounded-2xl border border-dashed border-white/20 bg-white/[0.025] px-6 py-12 text-center">
      <p className="font-medium text-white">{title}</p>
      {children && <p className="mx-auto mt-1 max-w-md text-sm text-slate-400">{children}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function Loading({ label = 'Loading…' }) {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-slate-400">
      <Spinner />
      <span className="text-sm">{label}</span>
    </div>
  );
}

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-white">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-400">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}
