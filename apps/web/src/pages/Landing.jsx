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
    <div className="min-h-screen overflow-hidden bg-[#08090d] text-white">
      <header className="relative z-10 mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <span className="flex items-center gap-2 text-lg font-semibold tracking-tight"><span className="grid h-7 w-7 place-items-center rounded-lg bg-gradient-to-br from-violet-400 to-cyan-300 text-sm text-slate-950">S</span>Sequence</span>
        <nav className="flex items-center gap-3">
          <Link to="/signin" className="text-sm font-medium text-slate-400 hover:text-white">
            Sign in
          </Link>
          <LinkButton to="/signup" size="sm">
            Get started
          </LinkButton>
        </nav>
      </header>

      <main>
        <section className="relative mx-auto max-w-5xl px-6 pb-24 pt-20 text-center sm:pt-28">
          <div className="absolute left-1/2 top-0 -z-0 h-80 w-80 -translate-x-1/2 rounded-full bg-violet-500/20 blur-[100px]" />
          <p className="relative mx-auto inline-flex rounded-full border border-white/10 bg-white/[.04] px-3 py-1 text-xs font-medium tracking-wide text-cyan-200">ONE HOME FOR YOUR PRESENCE + OPERATIONS</p>
          <h1 className="relative mt-6 text-5xl font-semibold leading-[.98] tracking-tight sm:text-7xl">
            Make the work feel<br />
            <span className="bg-gradient-to-r from-violet-300 via-white to-cyan-200 bg-clip-text text-transparent">effortlessly organised.</span>
          </h1>
          <p className="relative mx-auto mt-7 max-w-2xl text-lg leading-relaxed text-slate-400">
            Create a beautiful website for the world, then give your team a calm, capable system for the work behind it.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <LinkButton to="/signup" size="lg">
              Build one free
            </LinkButton>
            <span className="text-sm text-slate-400">Start with a proven template.</span>
          </div>
        </section>

        <section className="border-y border-white/10 bg-white/[.025] py-16">
          <div className="mx-auto grid max-w-6xl gap-5 px-6 sm:grid-cols-3">
            {STEPS.map((step, index) => (
              <div key={step.title} className="rounded-2xl border border-white/[.08] bg-[#10121a] p-6">
                <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-violet-400/15 text-sm font-medium text-violet-200">
                  {index + 1}
                </span>
                <h3 className="mt-4 font-semibold text-white">{step.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-400">{step.body}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-6 py-20">
          <h2 className="text-center text-3xl font-semibold tracking-tight text-white">
            Built around work that matters
          </h2>
          <div className="mt-8 grid gap-4 sm:grid-cols-3">
            {EXAMPLES.map((example) => (
              <div
                key={example.name}
                className="rounded-2xl border border-white/[.10] bg-white/[.035] p-6 transition hover:-translate-y-1 hover:border-cyan-300/30"
              >
                <h3 className="font-medium text-white">{example.name}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-400">{example.body}</p>
              </div>
            ))}
          </div>
          <p className="mt-8 text-center text-sm text-slate-400">
            Anything shaped like: someone submits it, someone approves it, everyone
            needs to know.
          </p>
        </section>

        <section className="border-t border-white/10 bg-gradient-to-b from-violet-500/10 to-transparent py-20">
          <div className="mx-auto max-w-2xl px-6 text-center">
            <h2 className="text-3xl font-semibold tracking-tight text-white">
              Start free
            </h2>
            <p className="mt-3 text-slate-400">
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

      <footer className="mx-auto max-w-6xl px-6 py-8 text-sm text-slate-500">
        <p>Sequence — built for small teams.</p>
      </footer>
    </div>
  );
}
