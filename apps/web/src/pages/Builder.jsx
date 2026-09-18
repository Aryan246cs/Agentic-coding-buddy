import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { api } from '../lib/api';
import Chrome from '../components/Chrome';
import PlanView from '../components/PlanView';
import RunLog from '../components/RunLog';
import FieldInput, { initialValues } from '../components/FieldInput';
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
  Select,
  StatusBadge,
} from '../components/ui';

const TABS = [
  { key: 'plan', label: 'What it does' },
  { key: 'test', label: 'Try it' },
  { key: 'team', label: 'Your team' },
  { key: 'runs', label: 'History' },
  { key: 'settings', label: 'Settings' },
];

export default function Builder() {
  const { projectId } = useParams();

  const [project, setProject] = useState(null);
  const [tab, setTab] = useState('plan');
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setProject(await api.getProject(projectId));
    } catch (err) {
      setError(err.message);
    }
  }, [projectId]);

  useEffect(() => {
    load();
  }, [load]);

  async function publish() {
    setBusy(true);
    setError(null);
    try {
      const updated = await api.publish(projectId);
      setProject({ ...project, ...updated });
      setNotice('Published. Anyone with the link and an invite can use it now.');
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function unpublish() {
    setBusy(true);
    try {
      await api.unpublish(projectId);
      setNotice('Taken offline. The link no longer works.');
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (!project && !error) return <Loading />;
  if (!project) {
    return (
      <Chrome>
        <Alert>{error}</Alert>
      </Chrome>
    );
  }

  const publicUrl = `${window.location.origin}${project.public_path}`;

  return (
    <Chrome wide>
      <PageHeader
        title={project.name}
        subtitle={
          project.is_published ? (
            <a href={project.public_path} target="_blank" rel="noreferrer" className="underline">
              {publicUrl}
            </a>
          ) : (
            'Not published yet — only you can see this.'
          )
        }
        actions={
          <>
            <Link to="/dashboard" className="text-sm text-slate-600 hover:text-slate-900">
              All apps
            </Link>
            {project.is_published ? (
              <>
                <Button variant="secondary" onClick={publish} loading={busy}>
                  {project.has_unpublished_changes ? 'Publish changes' : 'Republish'}
                </Button>
                <Button variant="danger" onClick={unpublish}>
                  Take offline
                </Button>
              </>
            ) : (
              <Button onClick={publish} loading={busy}>
                Publish
              </Button>
            )}
          </>
        }
      />

      {project.has_unpublished_changes && (
        <div className="mb-4">
          <Alert tone="warn">
            You have changes your team cannot see yet. Press "Publish changes" when
            you are ready.
          </Alert>
        </div>
      )}
      {notice && (
        <div className="mb-4">
          <Alert tone="good" onDismiss={() => setNotice(null)}>
            {notice}
          </Alert>
        </div>
      )}
      {error && (
        <div className="mb-4">
          <Alert onDismiss={() => setError(null)}>{error}</Alert>
        </div>
      )}

      <nav className="mb-6 flex gap-1 border-b border-slate-200">
        {TABS.map((item) => (
          <button
            key={item.key}
            onClick={() => setTab(item.key)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
              tab === item.key
                ? 'border-slate-900 text-slate-900'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            {item.label}
          </button>
        ))}
      </nav>

      {tab === 'plan' && <PlanTab project={project} onChanged={load} />}
      {tab === 'test' && <TestTab project={project} />}
      {tab === 'team' && <TeamTab project={project} />}
      {tab === 'runs' && <RunsTab project={project} />}
      {tab === 'settings' && <SettingsTab project={project} onChanged={load} />}
    </Chrome>
  );
}

// --------------------------------------------------------------------------

function PlanTab({ project, onChanged }) {
  const [instruction, setInstruction] = useState('');
  const [proposal, setProposal] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function propose(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setProposal(await api.revise(project.id, instruction));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function apply() {
    setBusy(true);
    try {
      await api.updateProject(project.id, { spec: proposal.spec });
      setProposal(null);
      setInstruction('');
      onChanged();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <Card className="p-5">
        <h3 className="font-medium text-slate-900">Change it by saying what you want</h3>
        <p className="mt-1 text-sm text-slate-600">
          For example: "also need HR to approve if the leave is more than 7 days".
        </p>
        <form onSubmit={propose} className="mt-3 flex flex-wrap gap-2">
          <Input
            value={instruction}
            onChange={(event) => setInstruction(event.target.value)}
            placeholder="What would you like to change?"
            className="min-w-64 flex-1"
          />
          <Button type="submit" loading={busy} disabled={instruction.length < 4}>
            Show me the change
          </Button>
        </form>
        {error && (
          <div className="mt-3">
            <Alert onDismiss={() => setError(null)}>{error}</Alert>
          </div>
        )}
      </Card>

      {proposal && (
        <Card className="border-blue-200 p-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="font-medium text-slate-900">Here is what would change</h3>
              <p className="text-sm text-slate-600">
                Nothing has been saved yet.
              </p>
            </div>
            <div className="flex gap-2">
              <Button onClick={apply} loading={busy}>
                Apply this
              </Button>
              <Button variant="secondary" onClick={() => setProposal(null)}>
                Cancel
              </Button>
            </div>
          </div>
          <PlanView plan={proposal.plan} />
        </Card>
      )}

      <Card className="p-6">
        <PlanView plan={project.plan} />
      </Card>
    </div>
  );
}

// --------------------------------------------------------------------------

function TestTab({ project }) {
  const spec = project.spec;
  const workflows = spec?.workflows || [];

  const [workflowKey, setWorkflowKey] = useState(workflows[0]?.key || '');
  const [approve, setApprove] = useState(true);
  const [values, setValues] = useState({});
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const workflow = workflows.find((item) => item.key === workflowKey);
  const entity = spec?.entities.find((item) => item.name === workflow?.trigger.entity);

  // The form a person would actually fill in, not every stored field.
  const formScreen = spec?.screens.find(
    (screen) => screen.type === 'form' && screen.submit_workflow === workflowKey,
  );
  const fields = (entity?.fields || []).filter((field) =>
    formScreen?.fields?.length ? formScreen.fields.includes(field.name) : true,
  );

  useEffect(() => {
    setValues(initialValues(fields));
    setResult(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workflowKey]);

  if (workflows.length === 0) {
    return <EmptyState title="Nothing to test">This app has no workflows yet.</EmptyState>;
  }

  async function run() {
    setBusy(true);
    setError(null);
    try {
      setResult(
        await api.testRun(project.id, { workflow_key: workflowKey, data: values, approve }),
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card className="p-5">
        <h3 className="font-medium text-slate-900">Try it with made-up details</h3>
        <p className="mt-1 text-sm text-slate-600">
          This runs for real — conditions, branches, approvals — but saves nothing and
          sends nothing.
        </p>

        <div className="mt-4 space-y-4">
          {workflows.length > 1 && (
            <Field label="Which one">
              <Select
                value={workflowKey}
                onChange={(event) => setWorkflowKey(event.target.value)}
              >
                {workflows.map((item) => (
                  <option key={item.key} value={item.key}>
                    {item.name}
                  </option>
                ))}
              </Select>
            </Field>
          )}

          {fields.map((field) => (
            <FieldInput
              key={field.name}
              field={field}
              value={values[field.name]}
              onChange={(name, value) => setValues({ ...values, [name]: value })}
              error={result?.field_errors?.[field.name]}
            />
          ))}

          <Field label="If someone has to approve it, pretend they">
            <Select
              value={approve ? 'approve' : 'reject'}
              onChange={(event) => setApprove(event.target.value === 'approve')}
            >
              <option value="approve">Approve it</option>
              <option value="reject">Reject it</option>
            </Select>
          </Field>

          <Button onClick={run} loading={busy} size="lg" className="w-full">
            Run the test
          </Button>
          {error && <Alert onDismiss={() => setError(null)}>{error}</Alert>}
        </div>
      </Card>

      <Card className="p-5">
        {result ? (
          <>
            <RunLog run={result.run} title="Test run" />
            {result.emails?.length > 0 && (
              <div className="mt-6 border-t border-slate-100 pt-4">
                <p className="text-sm font-medium text-slate-700">
                  Emails it would have sent
                </p>
                {result.emails.map((email, index) => (
                  <div key={index} className="mt-2 rounded bg-slate-50 p-3 text-sm">
                    <p className="font-medium text-slate-800">{email.subject}</p>
                    <p className="text-xs text-slate-500">To: {email.to.join(', ')}</p>
                    <p className="mt-1 text-slate-600">{email.body}</p>
                  </div>
                ))}
              </div>
            )}
            {result.records?.length > 0 && (
              <div className="mt-6 border-t border-slate-100 pt-4">
                <p className="text-sm font-medium text-slate-700">How the record ended up</p>
                {result.records.map((record) => (
                  <dl key={record.id} className="mt-2 rounded bg-slate-50 p-3 text-sm">
                    {Object.entries(record.data).map(([key, value]) => (
                      <div key={key} className="flex justify-between gap-4 py-0.5">
                        <dt className="text-slate-500">{key.replace(/_/g, ' ')}</dt>
                        <dd className="font-medium text-slate-800">{String(value)}</dd>
                      </div>
                    ))}
                  </dl>
                ))}
              </div>
            )}
          </>
        ) : (
          <EmptyState title="Fill in the form and press Run">
            You will see each step tick off, exactly as it will happen for real.
          </EmptyState>
        )}
      </Card>
    </div>
  );
}

// --------------------------------------------------------------------------

function TeamTab({ project }) {
  const [data, setData] = useState(null);
  const [form, setForm] = useState({ name: '', email: '', role: '' });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const result = await api.listMembers(project.id);
      setData(result);
      setForm((current) => ({ ...current, role: current.role || result.roles[0]?.name || '' }));
    } catch (err) {
      setError(err.message);
    }
  }, [project.id]);

  useEffect(() => {
    load();
  }, [load]);

  async function invite(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.inviteMember(project.id, form);
      setForm({ name: '', email: '', role: form.role });
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function remove(member) {
    if (!window.confirm(`Remove ${member.name}?`)) return;
    await api.removeMember(project.id, member.id);
    load();
  }

  if (!data) return <Loading />;

  return (
    <div className="space-y-6">
      {!project.is_published && (
        <Alert tone="warn">
          Publish the app before inviting people — their invite links will not work
          until you do.
        </Alert>
      )}

      <Card className="p-5">
        <h3 className="font-medium text-slate-900">Add someone</h3>
        <form onSubmit={invite} className="mt-3 grid gap-3 sm:grid-cols-4">
          <Input
            placeholder="Their name"
            value={form.name}
            onChange={(event) => setForm({ ...form, name: event.target.value })}
            required
          />
          <Input
            type="email"
            placeholder="Their email"
            value={form.email}
            onChange={(event) => setForm({ ...form, email: event.target.value })}
            required
          />
          <Select
            value={form.role}
            onChange={(event) => setForm({ ...form, role: event.target.value })}
          >
            {data.roles.map((role) => (
              <option key={role.name} value={role.name}>
                {role.label}
              </option>
            ))}
          </Select>
          <Button type="submit" loading={busy}>
            Invite
          </Button>
        </form>
        {error && (
          <div className="mt-3">
            <Alert onDismiss={() => setError(null)}>{error}</Alert>
          </div>
        )}
      </Card>

      {data.members.length === 0 ? (
        <EmptyState title="Nobody yet">
          Add the people who will use this app and send them their link.
        </EmptyState>
      ) : (
        <div className="space-y-2">
          {data.members.map((member) => {
            const label = data.roles.find((role) => role.name === member.role)?.label;
            const joinUrl = `${window.location.origin}/a/${project.slug}/join?token=${member.invite_token}`;
            return (
              <Card key={member.id} className="p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-slate-900">{member.name}</span>
                      <Badge>{label || member.role}</Badge>
                      {member.pending_invite && <Badge tone="waiting">Not joined yet</Badge>}
                    </div>
                    <p className="text-sm text-slate-500">{member.email}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    {member.pending_invite && (
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => {
                          navigator.clipboard?.writeText(joinUrl);
                        }}
                      >
                        Copy invite link
                      </Button>
                    )}
                    <Button variant="danger" size="sm" onClick={() => remove(member)}>
                      Remove
                    </Button>
                  </div>
                </div>
                {member.pending_invite && (
                  <p className="mt-2 break-all rounded bg-slate-50 px-2 py-1 text-xs text-slate-500">
                    {joinUrl}
                  </p>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

// --------------------------------------------------------------------------

function RunsTab({ project }) {
  const [runs, setRuns] = useState(null);

  useEffect(() => {
    api
      .listRuns(project.id)
      .then((result) => setRuns(result.runs))
      .catch(() => setRuns([]));
  }, [project.id]);

  if (runs === null) return <Loading />;
  if (runs.length === 0) {
    return (
      <EmptyState title="Nothing has happened yet">
        Once your team starts using the app, every request shows up here with each
        step it went through.
      </EmptyState>
    );
  }

  return (
    <div className="space-y-4">
      {runs.map((run) => (
        <Card key={run.id} className="p-5">
          <RunLog run={run} />
        </Card>
      ))}
    </div>
  );
}

// --------------------------------------------------------------------------

function SettingsTab({ project, onChanged }) {
  const [name, setName] = useState(project.name);
  const [slug, setSlug] = useState(project.slug);
  const [error, setError] = useState(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  async function save(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      await api.updateProject(project.id, { name, slug });
      setSaved(true);
      onChanged();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="max-w-lg p-5">
      <form onSubmit={save} className="space-y-4">
        <Field label="Name">
          <Input value={name} onChange={(event) => setName(event.target.value)} />
        </Field>
        <Field
          label="Link"
          hint={`${window.location.origin}/a/${slug}`}
          error={error}
        >
          <Input value={slug} onChange={(event) => setSlug(event.target.value)} />
        </Field>
        <div className="flex items-center gap-3">
          <Button type="submit" loading={busy}>
            Save
          </Button>
          {saved && <span className="text-sm text-emerald-600">Saved.</span>}
        </div>
      </form>

      <div className="mt-6 border-t border-slate-100 pt-4">
        <p className="text-sm text-slate-500">
          Status: <StatusBadge status={project.status} />
        </p>
      </div>
    </Card>
  );
}
