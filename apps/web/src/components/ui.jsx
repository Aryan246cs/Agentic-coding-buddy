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
  primary: 'bg-slate-900 text-white hover:bg-slate-700 disabled:bg-slate-300',
  secondary:
    'bg-white text-slate-700 border border-slate-300 hover:bg-slate-50 disabled:text-slate-400',
  danger: 'bg-white text-red-600 border border-red-200 hover:bg-red-50',
  approve: 'bg-emerald-600 text-white hover:bg-emerald-700 disabled:bg-emerald-300',
  reject: 'bg-white text-red-600 border border-red-300 hover:bg-red-50',
  ghost: 'text-slate-600 hover:text-slate-900 hover:bg-slate-100',
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
        'focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1',
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
      className={cx('rounded-xl border border-slate-200 bg-white', className)}
      {...props}
    >
      {children}
    </div>
  );
}

const TONES = {
  neutral: 'bg-slate-100 text-slate-700',
  good: 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200',
  bad: 'bg-red-50 text-red-700 ring-1 ring-red-200',
  waiting: 'bg-amber-50 text-amber-800 ring-1 ring-amber-200',
  info: 'bg-blue-50 text-blue-700 ring-1 ring-blue-200',
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
      <span className="mb-1.5 block text-sm font-medium text-slate-700">
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
  'w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 ' +
  'placeholder:text-slate-400 focus:border-slate-500 focus:outline-none focus:ring-1 ' +
  'focus:ring-slate-500 disabled:bg-slate-50';

export function Input({ className, ...props }) {
  return <input className={cx(inputClass, className)} {...props} />;
}

export function Textarea({ className, rows = 4, ...props }) {
  return <textarea rows={rows} className={cx(inputClass, 'resize-y', className)} {...props} />;
}

export function Select({ className, children, ...props }) {
  return (
    <select className={cx(inputClass, 'bg-white', className)} {...props}>
      {children}
    </select>
  );
}

export function Alert({ tone = 'bad', title, children, onDismiss }) {
  const styles = {
    bad: 'border-red-200 bg-red-50 text-red-800',
    good: 'border-emerald-200 bg-emerald-50 text-emerald-800',
    warn: 'border-amber-200 bg-amber-50 text-amber-900',
    info: 'border-blue-200 bg-blue-50 text-blue-800',
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
    <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50/50 px-6 py-12 text-center">
      <p className="font-medium text-slate-700">{title}</p>
      {children && <p className="mx-auto mt-1 max-w-md text-sm text-slate-500">{children}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function Loading({ label = 'Loading…' }) {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-slate-500">
      <Spinner />
      <span className="text-sm">{label}</span>
    </div>
  );
}

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-600">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}
