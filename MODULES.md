# Modules

11 modules. Each one is a real chunk of work with a clear "done" test.

The order matters — later modules assume earlier ones exist. The one exception is Module 10 (landing page), which is slotted at week 4 because that is when you launch, not because of any technical dependency.

| # | Module | Week | Days | Ships in |
|---|---|---|---|---|
| 1 | Foundation & Deployment Pipeline | 1 | 1.5 | — |
| 2 | Accounts, Login & Dashboard Shell | 1–2 | 2 | v0.1 |
| 3 | Spec Contracts & Data Layer | 2 | 1.5 | v0.1 |
| 4 | Website Builder | 3 | 3 | v0.1 |
| 5 | Publish & Hosting Layer | 3–4 | 1.5 | v0.1 |
| 10 | Landing Page & Onboarding | 4 | 1.5 | v0.1 |
| 6 | App Runtime (screens) | 5 | 2 | v0.2 |
| 7 | App Users, Roles & Permissions | 5 | 1 | v0.2 |
| 8 | Workflow Engine | 5–6 | 3 | v0.2 |
| 9 | AI Planning Layer | 7 | 2.5 | v0.2 |
| 11 | Limits, Usage & Launch Readiness | 8 | 2 | v0.2 |

Total ≈ 21.5 days against a 20-day budget. That overrun is why the cut list exists in `BUILD_PLAN.md`.

---

## Module 1 — Foundation & Deployment Pipeline
**Week 1 · 1.5 days**

Turn a laptop project into a deployable one.

**Work:**
- Restructure into `apps/web` (Next.js), `apps/api` (FastAPI), `packages/specs`
- Dockerfile for the API; `docker-compose.yml` for local dev (api + postgres + redis)
- Buy the domain; point DNS at Vercel
- Connect the repo to Vercel and Render, wire up auto-deploy on push to `main`
- Environment variable handling — `.env.example` in the repo, real values only in the hosting dashboards
- Alembic set up for migrations
- Sentry on both frontend and backend

**Done when:** you push a commit and a "coming soon" page appears at your domain, and `/api/health` responds from the backend. Both confirmed on your phone.

**Watch out for:** getting this working is genuinely fiddly — subfolder builds, CORS, env vars. Budget the full 1.5 days. It never goes smoothly and it only has to happen once.

---

## Module 2 — Accounts, Login & Dashboard Shell
**Week 1–2 · 2 days**

The platform account, and the frame everything else lives inside.

**Work:**
- Supabase Google sign-in, plus a `users` row created on first login
- Token verification middleware on the FastAPI side
- Protected routes; redirect to login when not signed in
- Dashboard layout: sidebar, two big buttons ("New Website", "New App"), list of your things
- Cards showing name, type, status (draft/published), last edited, and the public link
- Rename, duplicate, delete — with a confirmation on delete
- Account settings page (name, email, sign out, delete account)

**Done when:** two different Google accounts sign in and each sees only their own empty dashboard.

**Reuses:** the visual language of the existing `frontend/` — sidebar and project history are the same shapes, ported to Next.js.

---

## Module 3 — Spec Contracts & Data Layer
**Week 2 · 1.5 days**

The most important module in the project and the one with the least to show for it. Everything downstream depends on getting these shapes right.

**Work:**
- Pydantic models for `SiteSpec` and `AppSpec` (entities, fields, screens, roles, permissions, workflows) in `packages/specs`
- Generate TypeScript types from them so the frontend and backend cannot disagree
- Postgres schema: `users`, `projects`, `specs` (versioned), `records`, `app_users`, `app_memberships`, `workflow_runs`, `workflow_run_steps`, `notifications`, `usage_events`
- `records` table with `app_id` + `entity_name` + `data` (JSONB), with the right indexes
- **One data-access helper that takes `app_id` as a required argument.** Every record read and write goes through it. Never query `records` directly from anywhere else.
- Turn on row-level security on `records` as a second line of defence
- The validator: given a spec, confirm every screen type, field type, step type, role and reference is real and consistent — and return clear errors when not

**Done when:** you can hand-write a leave management spec as JSON, save it, load it back, and the validator accepts it. Change one step type to garbage and the validator explains exactly what is wrong.

**Watch out for:** the temptation to make the spec flexible. Flexible means the AI can produce things the runtime cannot render. Keep it tight.

---

## Module 4 — Website Builder
**Week 3 · 3 days**

The product that gets you your first users.

**Work:**
- **4–5 templates, hand-built.** Portfolio, freelancer, small business, event, personal. Hand-build these carefully — they set the quality ceiling for everything a user can make.
- `SiteSpec`: template choice, colour theme, headline, sections, contact details, social links, images
- AI call: description → filled `SiteSpec` (Haiku 4.5, structured output)
- Renderer: `SiteSpec` + template → a React page
- Builder screen: prompt bar, live preview, side panel to edit any text or colour by hand
- Regenerate, and undo
- Image handling: stock images by keyword to start; uploads later
- Mobile-responsive templates — most visitors will be on a phone

**Done when:** you describe a photographer's portfolio in one sentence and get a site that looks genuinely good on a phone, without editing anything.

**Reuses:** `PromptBar.jsx` and `Preview.jsx` are the right ideas. The preview becomes a React render of the spec instead of an iframe of generated HTML.

**Watch out for:** the pull toward "more templates." Five excellent ones beat twenty mediocre ones, and each one costs you real hours.

---

## Module 5 — Publish & Hosting Layer
**Week 3–4 · 1.5 days**

Shared machinery. Built once for websites, reused unchanged for apps.

**Work:**
- Slugs: auto-generate from the name, allow editing, enforce uniqueness, block reserved words
- `publish` and `unpublish` — set status, write a frozen spec version, bust the cache
- Redis caching of published specs, invalidated on publish
- `/s/<slug>` — server-rendered, edge-cached published website
- `/a/<slug>` — server-rendered published app shell (fills in once Module 6 exists)
- A friendly 404 for an unknown or unpublished slug
- Open Graph tags and favicon so shared links preview properly
- "Made with [product]" badge on free-tier sites

**Done when:** you publish a site, open the link in a private window on mobile data, and it loads in under a second.

**Watch out for:** slug collisions with your own routes. Reserve `api`, `login`, `dashboard`, `admin`, `s`, `a`, `www` before a user takes one.

---

## Module 10 — Landing Page & Onboarding
**Week 4 · 1.5 days** *(built here, out of numeric order, because this is when you launch)*

**Work:**
- Landing page: the promise in one line, the problem, how it works in three steps, two live examples, pricing, FAQ, call to action
- Everything readable and understandable **without logging in** — this is how strangers decide
- Pricing page (show the plans even if payment is not wired up)
- Onboarding: first-time users get 3 example prompts to click instead of a blank box
- Analytics (Plausible or Vercel), so you can see where people drop off
- Terms and privacy pages — plain, short, but present

**Done when:** you show it to someone who knows nothing about the project and they can tell you what it does in one sentence.

**Watch out for:** writing for developers. Your user is a clinic manager, not an engineer. No "AI-native," no "LLM," no "orchestration." Say "requests," "approvals," "your team."

---

## Module 6 — App Runtime (screens)
**Week 5 · 2 days**

Read an app spec and draw a working application.

**Work:**
- Screen renderers: **Form**, **Table**, **Record detail**, **List**
- Field renderers: text, long text, number, date, dropdown, yes/no — each with validation
- Navigation built from the spec, filtered by what the current role can see
- Record API: create, read, update, list — with filters, sort and pagination, all scoped by `app_id`
- Table features people expect: search, filter by status, sort by column
- The approval panel: pending items with Approve / Reject and a comment box
- The in-app notification bell

**Done when:** you hand-write the leave management spec and the app renders — you can submit a request through the form and see the row appear in the table.

**Watch out for:** scope creep into a page designer. The user gets to change labels, field order and visibility. Not layout.

---

## Module 7 — App Users, Roles & Permissions
**Week 5 · 1 day**

The people who use a built app — completely separate from your platform accounts.

**Work:**
- `app_users` table + email/password sign-up and login, scoped per app
- Session cookie scoped to that app's slug only
- Invite flow: the app owner adds an email and a role; an invite email goes out
- Roles defined by the spec (Employee, Manager, Admin, …)
- Permissions per role, enforced **server-side on every request** — which screens, which records (own vs. all vs. team), which actions
- A members screen for the owner to manage who has access
- Password reset

**Done when:** an employee logs into a published app and cannot see the manager's approval screen — and cannot reach it by typing the URL directly.

**Watch out for:** this is the security-critical module. Permission checks live in the API, never in the frontend. The frontend hiding a button is cosmetic.

---

## Module 8 — Workflow Engine
**Week 5–6 · 3 days**

The heart of the product.

**Work:**
- Step types: `trigger`, `create_record`, `update_record`, `condition`, `approval`, `notify_in_app`, `notify_email`, `ai_classify`
- The executor: walk the graph, pass data between steps, evaluate conditions, handle branches
- **Pause and resume at approvals** — persist the run state, wait for a human, pick up where it left off. This is the trickiest part; give it the most care.
- A jobs table for retries and background work. **No Celery, no queues** — a table and a small worker loop is enough and far less to go wrong.
- Every step logged: inputs, outputs, timing, result
- Run history screen: list of runs, status, duration; click in to see each step tick off
- Failure handling: mark the run failed, record which step and why, offer a retry
- Email sending via Resend
- Tests — this is the one place at this budget where tests pay for themselves

**Done when:** all three demo workflows run end to end from hand-written specs, including the multi-level expense approval, and every run shows a complete step-by-step log.

**Watch out for:** over-engineering. No distributed workflow platform, no event sourcing. A loop over a list of steps, with state in Postgres.

---

## Module 9 — AI Planning Layer
**Week 7 · 2.5 days**

Now that there is a runtime worth generating for, this module is surprisingly small.

**Work:**
- Planner: description → `AppSpec` + workflow specs, using structured output against the block catalog
- Validate the result; on failure, retry once with the validation errors fed back to the model
- **Plan screen** — the moment the product either earns trust or loses it. Show in plain English: who the users are, what screens exist, what gets stored, what happens step by step. Let the user edit or remove anything before building.
- Build: save spec → create records structure → open preview
- **Test runner:** run a workflow with sample data and animate each step passing. This is the signature feature — it is what convinces someone the thing actually works.
- Natural-language editing: "add HR approval if leave is over 7 days" → AI produces the changed spec → show a clear before/after → Apply or Cancel
- Token usage recorded per generation (shown to nobody yet)
- One AI wrapper module so the provider stays swappable

**Done when:** 16 of 20 descriptions you write produce a valid, sensible plan that builds and runs.

**Watch out for:** never applying an AI change without showing the user first. And never letting an unvalidated spec through — one broken published app destroys more trust than ten good ones build.

---

## Module 11 — Limits, Usage & Launch Readiness
**Week 8 · 2 days**

Turn a working demo into something you can leave running unattended.

**Work:**
- Usage counting: apps created, workflow runs, AI generations
- Free-tier limits actually enforced, with a clear message when hit (not a crash)
- Rate limits on the AI endpoints so one user cannot run up your bill
- Three one-click templates: leave, expenses, complaints
- Empty states, loading states, and error messages written for a non-developer
- Mobile check on every screen — the dashboard too, not just published pages
- Load-test one published app; find and fix the slowest query
- A backup that you have actually tested restoring
- Demo video, screenshots, updated landing page
- A feedback button on every page

**Done when:** you can hand the link to ten strangers and go to sleep.

---

## Summary of what each module leaves behind

| Module | The lasting thing it gives you |
|---|---|
| 1 | Push code → it is live |
| 2 | People have accounts |
| 3 | A spec is a real, validated, typed object |
| 4 | Product A works |
| 5 | Anything can become a public URL |
| 6 | A spec becomes screens you can use |
| 7 | The right people see the right things |
| 8 | Things actually happen, and you can see them happen |
| 9 | Plain English becomes all of the above |
| 10 | Strangers understand and sign up |
| 11 | You can walk away from it |
