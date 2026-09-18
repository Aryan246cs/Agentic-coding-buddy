/**
 * The plan, in the words the user reads before clicking Build.
 *
 * Every sentence here comes from the server, derived from the spec itself —
 * never from the model's prose. So what is shown is exactly what will be
 * built, which is the only reason approving it means anything.
 */

import { Badge, Card } from './ui';

function Section({ title, subtitle, children }) {
  return (
    <section>
      <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
        {title}
      </h3>
      {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
      <div className="mt-3">{children}</div>
    </section>
  );
}

function StepRow({ step, index }) {
  const isBranch = step.branches?.length > 0;

  return (
    <li className="relative pl-8">
      <span className="absolute left-0 top-0.5 flex h-6 w-6 items-center justify-center rounded-full bg-slate-100 text-xs font-medium text-slate-600">
        {index + 1}
      </span>
      <p className="text-sm text-slate-800">{step.sentence}</p>
      {isBranch && (
        <ul className="mt-1.5 space-y-1">
          {step.branches.map((branch) => (
            <li key={branch.when} className="text-xs text-slate-500">
              <span className="font-medium text-slate-600">If {branch.when}</span>
              {' → '}
              {branch.goes_to === '(finish)' ? 'finish' : branch.goes_to.replace(/_/g, ' ')}
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

export default function PlanView({ plan }) {
  if (!plan) return null;

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">{plan.name}</h2>
        <p className="mt-1 text-slate-600">{plan.description}</p>
      </div>

      <Section title="Who uses it">
        <div className="grid gap-3 sm:grid-cols-2">
          {plan.people.map((person) => (
            <Card key={person.name} className="p-4">
              <div className="flex items-center gap-2">
                <span className="font-medium text-slate-900">{person.label}</span>
                {person.is_admin && <Badge tone="info">Runs the app</Badge>}
                {person.can_approve && <Badge tone="good">Approves</Badge>}
              </div>
              {person.description && (
                <p className="mt-1 text-sm text-slate-600">{person.description}</p>
              )}
              <p className="mt-2 text-xs text-slate-500">
                Sees: {person.sees.join(', ') || 'nothing yet'}
              </p>
            </Card>
          ))}
        </div>
      </Section>

      <Section title="What gets saved">
        {plan.stores.map((store) => (
          <Card key={store.name} className="mb-3 p-4">
            <p className="font-medium text-slate-900">{store.label}</p>
            <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
              {store.fields.map((field) => (
                <li key={field.label} className="text-sm text-slate-600">
                  {field.label}
                  <span className="text-slate-400"> — {field.kind}</span>
                  {field.required && <span className="text-red-400"> *</span>}
                </li>
              ))}
            </ul>
          </Card>
        ))}
      </Section>

      <Section title="The pages they see">
        <ul className="space-y-2">
          {plan.pages.map((page) => (
            <li
              key={page.key}
              className="flex flex-wrap items-baseline justify-between gap-2 border-b border-slate-100 pb-2 text-sm"
            >
              <span className="font-medium text-slate-800">{page.title}</span>
              <span className="text-slate-500">
                {page.kind} · {page.who.join(', ')}
                {page.only_their_own && ' · only their own'}
              </span>
            </li>
          ))}
        </ul>
      </Section>

      {plan.workflows.map((workflow) => (
        <Section
          key={workflow.key}
          title={`What happens: ${workflow.name}`}
          subtitle={workflow.starts_when}
        >
          <ol className="space-y-4">
            {workflow.steps.map((step, index) => (
              <StepRow key={step.id} step={step} index={index} />
            ))}
          </ol>
        </Section>
      ))}
    </div>
  );
}
