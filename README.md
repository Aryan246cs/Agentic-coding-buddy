# Sequence

**Describe how your work happens. Get a working system with a link.**

> Working name — change it before launch. It appears in `apps/web/src` and in
> `index.html`.

For small teams running their operations on WhatsApp and spreadsheets. You
describe a process in plain words; you get a live system with a form, a queue
for approvals, a record of every decision, and a link to send your team.

Product thinking lives in [PRODUCT.md](PRODUCT.md), the schedule in
[BUILD_PLAN.md](BUILD_PLAN.md), and the work breakdown in [MODULES.md](MODULES.md).

---

## Running it

You need Python 3.11+ and Node 18+. Nothing else — no database to install, no
API key to get.

```bash
# Backend  → http://localhost:8000
uv sync --extra dev
uv run uvicorn app.main:app --app-dir apps/api --reload

# Frontend → http://localhost:5173   (second terminal)
cd apps/web && npm install && npm run dev
```

Open http://localhost:5173, create an account, and press **Build something new**.

### Tests

```bash
uv run pytest apps/api/tests -q
```

Tests never reach a real AI provider and never touch the development database.

### Optional configuration

Everything has a working default. Put overrides in `.env` at the repo root.

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | SQLite file | Swap for Postgres in production; no code change needed |
| `SECRET_KEY` | a dev value | **The app refuses to boot in production without a real one** |
| `ANTHROPIC_API_KEY` | — | Preferred for planning; most reliable at structured output |
| `GROQ_API_KEY` | — | Also works |
| `ENVIRONMENT` | `development` | Set to `production` to enable the safety checks |

**With no AI key at all, everything still works.** The planner falls back to a
matching built-in template. That is deliberate: if the product only works when
a model is reachable, the architecture is wrong.

---

## How it fits together

```
apps/web/          React + Vite + Tailwind
  pages/           landing, sign-in, dashboard, builder
  pages/runtime/   the published app, as its users see it
  components/      PlanView, RunLog, FieldInput, and the UI kit

apps/api/          FastAPI
  app/specs/       the spec schemas, the frozen block catalog, the validator
  app/engine/      the workflow executor, step handlers, expressions
  app/runtime/     tenant-scoped record access, field coercion
  app/ai/          provider seam + the planner
  app/routers/     auth, projects (builder), runtime (published apps)
  demos/           the three built-in templates
```

### The one rule

**The AI never writes code we run. It fills in a form.**

```
plain English → planner → JSON spec → validator → runtime → live app
```

The planner picks from a fixed catalog of about fifteen building blocks
(`app/specs/catalog.py`). It cannot invent one, cannot write SQL, and cannot
call anything we did not allow. The validator checks every cross-reference
before a spec is ever saved, and the runtime renders and executes what comes
out the other side.

This is why the product is predictable, cheap to run, safe to host on our own
domain, and fixable in one place for every customer at once.

### Things worth knowing before changing code

- **`RecordStore` cannot be built without a project id**, and every query it
  issues filters on it. Nothing else may query the `records` table.
- **Workflow steps are an ordered list with explicit branch targets**, not a
  free graph. Much easier to validate, and much easier for a model to get
  right. `WorkflowSpec.successors()` is the single definition of flow, shared
  by the validator and the executor so they cannot drift.
- **A run is a row, not a thread.** It stores a cursor and a context, so an
  approval can sit for a week at no cost. It also stores a snapshot of the
  workflow it started under, so editing a workflow never changes the outcome of
  something already in flight.
- **Test runs swap in a memory-backed store.** Real conditions, real branching,
  real approvals — nothing written, nothing sent.
- **Two token audiences that cannot be interchanged**: platform tokens for the
  people who build apps, per-app tokens for the people who use one.
- **Permissions are enforced in the API.** The frontend hiding a button is
  cosmetic.

---

## Where this is up to

Working end to end: sign up → build → read the plan → test it → publish →
invite colleagues → they submit requests → you approve → everyone is notified,
with a full run log.

Not built yet: the website builder UI (the backend and templates exist), email
delivery (queued to a table, no sender wired up), and deployment. See
[MODULES.md](MODULES.md).
