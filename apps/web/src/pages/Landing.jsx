import { Link } from 'react-router-dom';
import { LinkButton } from '../components/ui';

/**
 * The page a stranger lands on.
 *
 * Written for a clinic manager, not an engineer. No "AI-native", no "LLM", no
 * "workflow orchestration" — just requests, approvals and the people involved.
 */

const STEPS = [
  {
    title: 'Describe how it works today',
    body: '"Staff send me leave requests on WhatsApp. I approve them. Half the time I forget."',
  },
  {
    title: 'Check we understood',
    body: 'We show you the plan in plain English — who does what, what gets saved, what happens next. Change anything before we build it.',
  },
  {
    title: 'Send your team the link',
    body: 'They sign in, submit requests, and you approve them in one place. Every decision recorded, with who and when.',
  },
];

const EXAMPLES = [
  { name: 'Leave requests', body: 'Staff ask. Their manager approves. Everyone gets told.' },
  {
    name: 'Expense claims',
    body: 'Small amounts clear themselves. Big ones go to whoever should see them.',
  },
  {
    name: 'Customer complaints',
    body: 'Urgent ones reach a manager. The rest go to your support team.',
  },
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-white">
      <header className="mx-auto flex max-w-5xl items-center justify-between px-6 py-5">
        <span className="text-lg font-semibold tracking-tight text-slate-900">Sequence</span>
        <nav className="flex items-center gap-3">
          <Link to="/signin" className="text-sm font-medium text-slate-600 hover:text-slate-900">
            Sign in
          </Link>
          <LinkButton to="/signup" size="sm">
            Get started
          </LinkButton>
        </nav>
      </header>

      <main>
        <section className="mx-auto max-w-3xl px-6 pb-20 pt-16 text-center sm:pt-24">
          <h1 className="text-4xl font-semibold leading-tight tracking-tight text-slate-900 sm:text-5xl">
            Describe how your work happens.
            <br />
            <span className="text-slate-500">Get a working system with a link.</span>
          </h1>
          <p className="mx-auto mt-6 max-w-xl text-lg leading-relaxed text-slate-600">
            If your team runs on WhatsApp messages and a spreadsheet, this turns that
            into something with a form, a queue, and a record of who approved what.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <LinkButton to="/signup" size="lg">
              Build one free
            </LinkButton>
            <span className="text-sm text-slate-500">Takes about two minutes.</span>
          </div>
        </section>

        <section className="border-y border-slate-200 bg-slate-50 py-16">
          <div className="mx-auto grid max-w-5xl gap-8 px-6 sm:grid-cols-3">
            {STEPS.map((step, index) => (
              <div key={step.title}>
                <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-slate-900 text-sm font-medium text-white">
                  {index + 1}
                </span>
                <h3 className="mt-4 font-semibold text-slate-900">{step.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">{step.body}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-5xl px-6 py-16">
          <h2 className="text-center text-2xl font-semibold tracking-tight text-slate-900">
            What people build
          </h2>
          <div className="mt-8 grid gap-4 sm:grid-cols-3">
            {EXAMPLES.map((example) => (
              <div
                key={example.name}
                className="rounded-xl border border-slate-200 bg-white p-5"
              >
                <h3 className="font-medium text-slate-900">{example.name}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">{example.body}</p>
              </div>
            ))}
          </div>
          <p className="mt-8 text-center text-sm text-slate-500">
            Anything shaped like: someone submits it, someone approves it, everyone
            needs to know.
          </p>
        </section>

        <section className="border-t border-slate-200 bg-slate-50 py-16">
          <div className="mx-auto max-w-2xl px-6 text-center">
            <h2 className="text-2xl font-semibold tracking-tight text-slate-900">
              Start free
            </h2>
            <p className="mt-3 text-slate-600">
              One app and one website, free forever. Pay only when your team actually
              uses it.
            </p>
            <div className="mt-6">
              <LinkButton to="/signup" size="lg">
                Create your account
              </LinkButton>
            </div>
          </div>
        </section>
      </main>

      <footer className="mx-auto max-w-5xl px-6 py-8 text-sm text-slate-500">
        <p>Sequence — built for small teams.</p>
      </footer>
    </div>
  );
}
