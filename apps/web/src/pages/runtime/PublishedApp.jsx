/**
 * A published app, as its users see it.
 *
 * Completely separate from the builder: its own sign-in, its own session, and
 * only the pages this person's role is allowed. What it draws comes from the
 * server, which re-checks every permission on every request — this file is
 * presentation, never the gate.
 */

import { useCallback, useEffect, useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';

import { appToken, runtimeApi } from '../../lib/api';
import FieldInput, { displayValue, initialValues } from '../../components/FieldInput';
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Field,
  Input,
  Loading,
  PageHeader,
  Spinner,
  StatusBadge,
} from '../../components/ui';

export default function PublishedApp() {
  const { slug } = useParams();
  const [params] = useSearchParams();
  const inviteToken = params.get('token');

  const [session, setSession] = useState(null);
  const [info, setInfo] = useState(null);
  const [screenKey, setScreenKey] = useState(null);
  const [loading, setLoading] = useState(true);
  const [fatal, setFatal] = useState(null);

  const loadSession = useCallback(async () => {
    if (!appToken.get(slug)) {
      setSession(null);
      setLoading(false);
      return;
    }
    try {
      const me = await runtimeApi.me(slug);
      setSession(me);
      setScreenKey((current) => current || me.nav[0]?.key || null);
    } catch {
      appToken.clear(slug);
      setSession(null);
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    runtimeApi
      .info(slug)
      .then(setInfo)
      .catch((err) => setFatal(err.message));
    loadSession();
  }, [slug, loadSession]);

  if (fatal) {
    return (
      <div className="app-shell flex min-h-screen items-center justify-center px-4">
        <Card className="max-w-md p-8 text-center">
          <p className="text-lg font-medium text-slate-900">Nothing here</p>
          <p className="mt-2 text-sm text-slate-600">{fatal}</p>
        </Card>
      </div>
    );
  }

  if (loading || !info) return <Loading />;

  if (!session) {
    return (
      <SignInToApp
        slug={slug}
        info={info}
        inviteToken={inviteToken}
        onSignedIn={() => {
          setLoading(true);
          loadSession();
        }}
      />
    );
  }

  return (
    <AppShell
      slug={slug}
      session={session}
      screenKey={screenKey}
      onNavigate={setScreenKey}
      onSignOut={() => {
        appToken.clear(slug);
        setSession(null);
      }}
    />
  );
}

// --------------------------------------------------------------------------

function SignInToApp({ slug, info, inviteToken, onSignedIn }) {
  const joining = Boolean(inviteToken);
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = joining
        ? await runtimeApi.join(slug, { token: inviteToken, password: form.password })
        : await runtimeApi.login(slug, form);
      appToken.set(slug, result.token);
      onSignedIn();
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <div className="app-shell flex min-h-screen items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm">
        <Card className="p-6">
          <h1 className="text-xl font-semibold text-slate-900">{info.name}</h1>
          <p className="mt-1 text-sm text-slate-600">
            {joining ? 'Pick a password to finish joining.' : 'Sign in to continue.'}
          </p>

          <form onSubmit={submit} className="mt-6 space-y-4">
            {error && <Alert>{error}</Alert>}

            {!joining && (
              <Field label="Email" required>
                <Input
                  type="email"
                  value={form.email}
                  onChange={(event) => setForm({ ...form, email: event.target.value })}
                  autoComplete="email"
                  required
                />
              </Field>
            )}

            <Field
              label={joining ? 'Choose a password' : 'Password'}
              hint={joining ? 'At least 8 characters.' : null}
              required
            >
              <Input
                type="password"
                value={form.password}
                onChange={(event) => setForm({ ...form, password: event.target.value })}
                autoComplete={joining ? 'new-password' : 'current-password'}
                required
              />
            </Field>

            <Button type="submit" size="lg" loading={busy} className="w-full">
              {joining ? 'Join' : 'Sign in'}
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
}

// --------------------------------------------------------------------------

function AppShell({ slug, session, screenKey, onNavigate, onSignOut }) {
  const [bell, setBell] = useState({ unread: 0, notifications: [] });
  const [showBell, setShowBell] = useState(false);
  const [version, setVersion] = useState(0);

  const refreshBell = useCallback(() => {
    runtimeApi
      .notifications(slug)
      .then(setBell)
      .catch(() => {});
  }, [slug]);

  useEffect(() => {
    refreshBell();
  }, [refreshBell, version]);

  return (
    <div className="app-shell min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-3">
            <span className="font-semibold text-slate-900">{session.app.name}</span>
            <Badge>{session.user.role_label}</Badge>
          </div>

          <div className="flex items-center gap-4">
            <div className="relative">
              <button
                onClick={() => {
                  setShowBell(!showBell);
                  if (!showBell && bell.unread > 0) {
                    runtimeApi.markRead(slug).then(refreshBell);
                  }
                }}
                className="relative rounded p-1.5 text-slate-600 hover:bg-slate-100"
              >
                🔔
                {bell.unread > 0 && (
                  <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-medium text-white">
                    {bell.unread}
                  </span>
                )}
              </button>

              {showBell && (
                <div className="absolute right-0 z-20 mt-2 w-80 rounded-lg border border-slate-200 bg-white shadow-lg">
                  {bell.notifications.length === 0 ? (
                    <p className="px-4 py-6 text-center text-sm text-slate-500">
                      Nothing yet.
                    </p>
                  ) : (
                    <ul className="max-h-96 divide-y divide-slate-100 overflow-y-auto">
                      {bell.notifications.map((item) => (
                        <li key={item.id} className="px-4 py-3">
                          <p className="text-sm font-medium text-slate-800">{item.title}</p>
                          <p className="mt-0.5 text-sm text-slate-600">{item.body}</p>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>

            <span className="hidden text-sm text-slate-600 sm:inline">
              {session.user.name}
            </span>
            <button
              onClick={onSignOut}
              className="text-sm font-medium text-slate-600 hover:text-slate-900"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-6xl gap-8 px-6 py-8">
        <nav className="w-52 shrink-0 space-y-1">
          {session.nav.map((item) => (
            <button
              key={item.key}
              onClick={() => onNavigate(item.key)}
              className={`block w-full rounded-lg px-3 py-2 text-left text-sm font-medium transition-colors ${
                screenKey === item.key
                  ? 'bg-slate-900 text-white'
                  : 'text-slate-700 hover:bg-slate-200/60'
              }`}
            >
              {item.title}
            </button>
          ))}
        </nav>

        <div className="min-w-0 flex-1">
          {screenKey ? (
            <Screen
              slug={slug}
              screenKey={screenKey}
              version={version}
              onChanged={() => setVersion((value) => value + 1)}
            />
          ) : (
            <EmptyState title="Nothing to show">
              Your role has no pages yet. Ask whoever runs this app.
            </EmptyState>
          )}
        </div>
      </div>
    </div>
  );
}

// --------------------------------------------------------------------------

function Screen({ slug, screenKey, version, onChanged }) {
  const [screen, setScreen] = useState(null);
  const [search, setSearch] = useState('');
  const [error, setError] = useState(null);

  useEffect(() => {
    setScreen(null);
    setError(null);
    runtimeApi
      .screen(slug, screenKey, { search })
      .then(setScreen)
      .catch((err) => setError(err.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug, screenKey, search, version]);

  if (error) return <Alert>{error}</Alert>;
  if (!screen) return <Loading />;

  if (screen.type === 'form') {
    return <FormScreen slug={slug} screen={screen} onSubmitted={onChanged} />;
  }
  if (screen.type === 'approvals') {
    return <ApprovalsScreen slug={slug} screen={screen} onDecided={onChanged} />;
  }
  return (
    <TableScreen screen={screen} search={search} onSearch={setSearch} />
  );
}

function FormScreen({ slug, screen, onSubmitted }) {
  const [values, setValues] = useState(() => initialValues(screen.fields));
  const [fieldErrors, setFieldErrors] = useState({});
  const [error, setError] = useState(null);
  const [done, setDone] = useState(null);
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setFieldErrors({});
    setDone(null);
    try {
      const result = await runtimeApi.submit(slug, screen.key, values);
      setValues(initialValues(screen.fields));
      setDone(
        result.workflow?.status === 'waiting_approval'
          ? 'Sent. Someone will review it and you will be told the outcome.'
          : 'Sent.',
      );
      onSubmitted();
    } catch (err) {
      setError(err.message);
      setFieldErrors(err.fieldErrors || {});
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader title={screen.title} />
      <Card className="max-w-xl p-6">
        <form onSubmit={submit} className="space-y-4">
          {done && <Alert tone="good">{done}</Alert>}
          {error && Object.keys(fieldErrors).length === 0 && <Alert>{error}</Alert>}

          {screen.fields.map((field) => (
            <FieldInput
              key={field.name}
              field={field}
              value={values[field.name]}
              onChange={(name, value) => setValues({ ...values, [name]: value })}
              error={fieldErrors[field.name]}
              disabled={busy}
            />
          ))}

          <Button type="submit" size="lg" loading={busy}>
            Send
          </Button>
        </form>
      </Card>
    </>
  );
}

function TableScreen({ screen, search, onSearch }) {
  const rows = screen.records || [];

  return (
    <>
      <PageHeader
        title={screen.title}
        subtitle={`${screen.total} ${screen.total === 1 ? screen.entity.label.toLowerCase() : screen.entity.plural.toLowerCase()}`}
        actions={
          <Input
            value={search}
            onChange={(event) => onSearch(event.target.value)}
            placeholder="Search…"
            className="w-56"
          />
        }
      />

      {rows.length === 0 ? (
        <EmptyState title={screen.empty_text || 'Nothing here yet'} />
      ) : (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-slate-200 bg-slate-50">
                <tr>
                  {screen.fields.map((field) => (
                    <th
                      key={field.name}
                      className="px-4 py-2.5 text-left font-medium text-slate-600"
                    >
                      {field.label}
                    </th>
                  ))}
                  <th className="px-4 py-2.5 text-left font-medium text-slate-600">
                    Submitted by
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rows.map((row) => (
                  <tr key={row.id} className="hover:bg-slate-50">
                    {screen.fields.map((field) => (
                      <td key={field.name} className="px-4 py-2.5 text-slate-800">
                        {field.name === 'status' || field.name === 'priority' ? (
                          <StatusBadge status={row.values[field.name]} />
                        ) : (
                          displayValue(field, row.values[field.name])
                        )}
                      </td>
                    ))}
                    <td className="px-4 py-2.5 text-slate-500">
                      {row.submitted_by || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </>
  );
}

function ApprovalsScreen({ slug, screen, onDecided }) {
  const [deciding, setDeciding] = useState(null);
  const [notes, setNotes] = useState({});
  const [error, setError] = useState(null);

  async function decide(approvalId, approved) {
    setDeciding(approvalId);
    setError(null);
    try {
      await runtimeApi.decide(slug, approvalId, {
        approved,
        note: notes[approvalId] || null,
      });
      onDecided();
    } catch (err) {
      setError(err.message);
    } finally {
      setDeciding(null);
    }
  }

  const items = screen.approvals || [];

  return (
    <>
      <PageHeader
        title={screen.title}
        subtitle={
          items.length === 0
            ? 'All clear.'
            : `${items.length} waiting on you`
        }
      />

      {error && (
        <div className="mb-4">
          <Alert onDismiss={() => setError(null)}>{error}</Alert>
        </div>
      )}

      {items.length === 0 ? (
        <EmptyState title={screen.empty_text || 'Nothing waiting on you'} />
      ) : (
        <div className="space-y-4">
          {items.map((item) => (
            <Card key={item.approval_id} className="p-5">
              <p className="font-medium text-slate-900">{item.prompt}</p>
              <p className="mt-0.5 text-sm text-slate-500">
                From {item.record.submitted_by || 'someone'}
              </p>

              <dl className="mt-4 grid gap-x-8 gap-y-1.5 sm:grid-cols-2">
                {screen.fields.map((field) => (
                  <div key={field.name} className="flex justify-between gap-4 text-sm">
                    <dt className="text-slate-500">{field.label}</dt>
                    <dd className="text-right font-medium text-slate-800">
                      {displayValue(field, item.record.values[field.name])}
                    </dd>
                  </div>
                ))}
              </dl>

              <div className="mt-4 flex flex-wrap items-center gap-2">
                <Input
                  value={notes[item.approval_id] || ''}
                  onChange={(event) =>
                    setNotes({ ...notes, [item.approval_id]: event.target.value })
                  }
                  placeholder="Add a note (optional)"
                  className="min-w-48 flex-1"
                />
                <Button
                  variant="approve"
                  loading={deciding === item.approval_id}
                  onClick={() => decide(item.approval_id, true)}
                >
                  Approve
                </Button>
                <Button
                  variant="reject"
                  disabled={deciding === item.approval_id}
                  onClick={() => decide(item.approval_id, false)}
                >
                  Reject
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
