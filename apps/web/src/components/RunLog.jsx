/**
 * A workflow run, step by step.
 *
 * This is the feature that makes people trust the thing. Someone who has never
 * written software watches each step tick off and can see exactly what their
 * system did and why it branched the way it did.
 */

import { Badge, StatusBadge } from './ui';

const MARKS = {
  ok: { glyph: '✓', className: 'bg-emerald-100 text-emerald-700' },
  skipped: { glyph: '–', className: 'bg-slate-100 text-slate-500' },
  waiting: { glyph: '⏳', className: 'bg-amber-100 text-amber-700' },
  failed: { glyph: '✕', className: 'bg-red-100 text-red-700' },
};

function Mark({ status }) {
  const mark = MARKS[status] || MARKS.skipped;
  return (
    <span
      className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${mark.className}`}
    >
      {mark.glyph}
    </span>
  );
}

export default function RunLog({ run, title }) {
  if (!run) return null;

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <h3 className="font-medium text-slate-900">
            {title || `Run #${run.sequence}`}
          </h3>
          <StatusBadge status={run.status} />
          {run.is_test && <Badge tone="info">Test</Badge>}
        </div>
        {run.duration_seconds != null && (
          <span className="text-xs text-slate-500">
            Finished in {run.duration_seconds}s
          </span>
        )}
      </div>

      {run.status === 'failed' && run.error && (
        <p className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          Stopped at <span className="font-medium">{run.failed_step}</span>: {run.error}
        </p>
      )}

      <ol className="mt-4 space-y-3">
        {run.steps.map((step) => (
          <li key={`${step.position}-${step.step_id}`} className="flex gap-3">
            <Mark status={step.status} />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-slate-800">{step.label}</p>
              {step.message && (
                <p className="mt-0.5 text-sm text-slate-600">{step.message}</p>
              )}
              {step.detail?.simulated && (
                <p className="mt-0.5 text-xs text-slate-400">
                  Nothing was actually sent — this was a test.
                </p>
              )}
            </div>
            {step.duration_ms != null && step.duration_ms > 0 && (
              <span className="shrink-0 text-xs text-slate-400">{step.duration_ms}ms</span>
            )}
          </li>
        ))}
      </ol>

      {run.status === 'waiting_approval' && (
        <p className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          This is waiting for someone to approve it. It will carry on by itself once
          they do — even if that is next week.
        </p>
      )}
    </div>
  );
}
