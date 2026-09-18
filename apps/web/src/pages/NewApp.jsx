import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

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
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [planning, setPlanning] = useState(false);
  const [building, setBuilding] = useState(false);

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
        title="What do you need?"
        subtitle="Describe how it works in your team today. Plain words are fine."
      />

      <form onSubmit={makePlan}>
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
      </form>

      {!result && !planning && (
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

      {result && (
        <div className="mt-10">
          {result.offline && (
            <div className="mb-6">
              <Alert tone="warn" title="Built from a template">
                No AI key is configured, so we started you from the closest
                ready-made app. You can change anything about it.
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
