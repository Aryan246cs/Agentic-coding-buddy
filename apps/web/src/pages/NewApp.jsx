import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Blocks, Sparkles } from 'lucide-react';

import { api } from '../lib/api';
import Chrome from '../components/Chrome';
import PlanView from '../components/PlanView';
import { Alert, Button, Card, PageHeader, Textarea } from '../components/ui';

/** Clicking one of these beats staring at an empty box. */
const EXAMPLES = [
  'Staff request leave. Their manager approves or rejects it, and the person who asked gets told either way.',
  'Employees claim expenses. Anything under ₹5,000 is approved automatically, up to ₹50,000 needs a manager, above that needs a director.',
  'Customers send us complaints through a form. Urgent ones should reach the manager, the rest go to our support team.',
];

export default function NewApp() {
  const navigate = useNavigate();

  const [description, setDescription] = useState('');
  const [mode, setMode] = useState('custom');
  const [templates, setTemplates] = useState([]);
  const [startingTemplate, setStartingTemplate] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [planning, setPlanning] = useState(false);
  const [building, setBuilding] = useState(false);

  async function browseTemplates() {
    setMode('template'); setResult(null); setError(null);
    try { const data = await api.templates(); setTemplates(data.apps || []); }
    catch (err) { setError(err.message); }
  }

  async function startFromTemplate(key) {
    setStartingTemplate(key); setError(null);
    try { const project = await api.createFromTemplate(key); navigate(`/projects/${project.id}`); }
    catch (err) { setError(err.message); setStartingTemplate(null); }
  }

  async function makePlan(event) {
    event?.preventDefault();
    setPlanning(true);
    setError(null);
    setResult(null);
    try {
      setResult(await api.planApp(description));
    } catch (err) {
      setError(err.message);
    } finally {
      setPlanning(false);
    }
  }

  async function build() {
    setBuilding(true);
    setError(null);
    try {
      const project = await api.createProject({
        kind: 'app',
        spec: result.spec,
        source_prompt: description,
      });
      navigate(`/projects/${project.id}`);
    } catch (err) {
      setError(err.message);
      setBuilding(false);
    }
  }

  return (
    <Chrome>
      <PageHeader
        title="Build a workflow"
        subtitle="Start from a ready-made example or describe the process your team actually needs."
      />

      <div className="mb-7 grid gap-4 sm:grid-cols-2">
        <button onClick={() => setMode('custom')} className={`rounded-2xl border p-5 text-left transition ${mode === 'custom' ? 'border-violet-400/70 bg-violet-400/[.08]' : 'border-white/10 bg-white/[.025] hover:border-white/25'}`}>
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-violet-400/10 text-violet-200"><Sparkles size={20} /></span><h2 className="mt-4 text-lg font-semibold text-white">Describe a custom workflow</h2><p className="mt-1 text-sm leading-6 text-slate-400">Tell the AI who submits requests, what happens next, and what your own process needs.</p>
        </button>
        <button onClick={browseTemplates} className={`rounded-2xl border p-5 text-left transition ${mode === 'template' ? 'border-cyan-300/60 bg-cyan-300/[.06]' : 'border-white/10 bg-white/[.025] hover:border-white/25'}`}>
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-cyan-300/10 text-cyan-200"><Blocks size={20} /></span><h2 className="mt-4 text-lg font-semibold text-white">Start with a template</h2><p className="mt-1 text-sm leading-6 text-slate-400">Open an example workflow, then make its roles, forms, and approval rules your own.</p>
        </button>
      </div>

      {mode === 'template' && <Card className="mb-8 p-5"><div className="flex items-center justify-between"><div><h2 className="font-semibold text-white">Workflow starters</h2><p className="mt-1 text-sm text-slate-400">These are starting points. You can change the full workflow afterwards.</p></div><button onClick={() => setMode('custom')} className="text-sm text-violet-200 hover:text-white">Describe my own →</button></div><div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{templates.map((template) => <div key={template.key} className="flex flex-col rounded-xl border border-white/10 bg-white/[.025] p-4"><h3 className="font-medium text-white">{template.name}</h3><p className="mt-2 flex-1 text-sm leading-5 text-slate-400">{template.blurb}</p><p className="mt-3 text-xs text-slate-500">{template.roles?.join(' · ')}</p><Button className="mt-4" size="sm" variant="secondary" loading={startingTemplate === template.key} onClick={() => startFromTemplate(template.key)}>Open this starter</Button></div>)}</div></Card>}

      {mode === 'custom' && <form onSubmit={makePlan}>
        <Textarea
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          rows={5}
          placeholder="Staff send me leave requests on WhatsApp and I approve them…"
          className="text-base"
        />

        <div className="mt-3 flex flex-wrap items-center gap-3">
          <Button type="submit" size="lg" loading={planning} disabled={description.length < 15}>
            {planning ? 'Working it out…' : 'Show me the plan'}
          </Button>
          <span className="text-sm text-slate-500">
            Nothing is built yet — you will see the plan first.
          </span>
        </div>
      </form>}

      {mode === 'custom' && !result && !planning && (
        <div className="mt-8">
          <p className="text-sm font-medium text-slate-600">Or try one of these:</p>
          <div className="mt-3 space-y-2">
            {EXAMPLES.map((example) => (
              <button
                key={example}
                onClick={() => setDescription(example)}
                className="block w-full rounded-lg border border-slate-200 bg-white px-4 py-3 text-left text-sm text-slate-700 hover:border-slate-400 hover:bg-slate-50"
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      )}

      {error && (
        <div className="mt-6">
          <Alert onDismiss={() => setError(null)}>{error}</Alert>
        </div>
      )}

      {mode === 'custom' && result && (
        <div className="mt-10">
          {result.offline && (
            <div className="mb-6">
              <Alert tone="warn" title="Started you from a ready-made app">
                {result.fallback_reason ||
                  'No AI is set up here, so we started you from the closest ready-made app.'}{' '}
                You can change anything about it.
              </Alert>
            </div>
          )}

          <Card className="p-6">
            <p className="mb-6 text-sm font-medium text-slate-500">
              Here is what we understood. Check it before we build.
            </p>

            <PlanView plan={result.plan} />

            {result.warnings?.length > 0 && (
              <div className="mt-8">
                <Alert tone="warn" title="Worth a look">
                  <ul className="list-inside list-disc space-y-1">
                    {result.warnings.map((warning) => (
                      <li key={warning.path}>{warning.message}</li>
                    ))}
                  </ul>
                </Alert>
              </div>
            )}
          </Card>

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <Button size="lg" loading={building} onClick={build}>
              Build this
            </Button>
            <Button variant="secondary" size="lg" onClick={makePlan} loading={planning}>
              Try again
            </Button>
            <span className="text-sm text-slate-500">
              You can still change everything afterwards.
            </span>
          </div>
        </div>
      )}
    </Chrome>
  );
}
