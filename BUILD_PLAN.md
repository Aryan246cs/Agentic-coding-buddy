# Build Plan — From Here to Live Users

## The honest budget

8 weeks × 2.5 days = **20 working days**. Roughly 160 hours.

That is not enough to build everything in `PRODUCT.md` and launch it well. So we do not try. We **launch twice**:

| | When | What ships | Why |
|---|---|---|---|
| **v0.1** | End of week 4 | Landing page + login + Website Builder, on a real domain | Real users, real signups, and the boring infrastructure is proven before the hard part starts |
| **v0.2** | End of week 8 | Workflow Builder | The actual product, shipped to an audience that already exists |

Shipping at week 4 is the single most important decision in this plan. It de-risks deployment, gives you feedback while you still have time to use it, and means that if week 8 slips, you are still live.

---

## Where you are today

What exists in this folder:

- ✅ FastAPI backend with 3 endpoints (`api.py`)
- ✅ LangGraph agent: planner → architect → coder, on Groq (`agent/`)
- ✅ React + Vite + Tailwind UI with Monaco editor, file tree, live preview (`frontend/`)
- ✅ Generated projects land on local disk (`projects/`)

What does not exist:

- ❌ No database. Everything is files on your laptop.
- ❌ No login, no accounts, no users.
- ❌ No deployment. Nothing is on the internet.
- ❌ No publishing. Nothing can be shared with a link.
- ❌ No multi-tenancy. There is no concept of "whose project is this."

**So: about 25% of the plumbing exists, and it is the front 25%.** The prompt bar, the preview pane, the project list and the generation loop are all genuinely reusable ideas. The code itself gets ported, not copied, because the target is Next.js and a database.

### One decision to make on day one

The current agent writes free-form HTML/CSS/JS to disk. **Do not publish that to the internet.** Reasons:

1. **Security.** Arbitrary generated JavaScript on `ourdomain.com` can read cookies from your other pages. That includes login cookies.
2. **Quality.** Free-form output is unpredictable. One in five will be broken, and you will not know which one.
3. **Speed.** Rendering from a spec is instant and cacheable. Serving generated files is neither.

So the site builder changes shape: **AI fills a structured site spec (headline, sections, images, colours), and our template renders it.** Same user experience, same prompt bar, far more reliable. Keep the current free-form generator as a hidden "advanced" toy if you like, but it is not on the launch path.

---

## The stack, decided

No more evaluating. These are the choices.

| Layer | Choice | Cost | Why this one |
|---|---|---|---|
| Frontend | **Next.js 15** (App Router) + TypeScript + Tailwind + shadcn/ui | — | Server rendering is what makes published pages fast. You need it for `/s/` and `/a/` routes. |
| Frontend hosting | **Vercel** | Free → $20/mo | Zero-config, instant deploys, edge caching. ⚠️ See warning below. |
| Backend | **FastAPI**, Python 3.11, in Docker | — | You already know it and it is already written. |
| Backend hosting | **Render** (or DigitalOcean App Platform if you have credits) | $7/mo | Must be a paid always-on plan. Free plans sleep. |
| Database | **Supabase** (managed Postgres + Google sign-in + storage) | Free → $25/mo | One service covers three needs. Pick the Mumbai or Singapore region. |
| Cache | **Upstash Redis** | Free | Caches published specs so page loads skip the database. |
| Email | **Resend** | Free (3,000/mo) | Workflow notifications. Simple API. |
| AI | **Claude** via the `anthropic` Python SDK | Per use (~₹2/build) | Reliable structured JSON. Keep it behind one wrapper module so it is swappable. |
| Domain | Namecheap / Cloudflare | ~₹1,000/yr | Buy this in week 1. Everything else depends on it. |
| Error tracking | **Sentry** | Free | You will not find bugs in a published app any other way. |

**Running cost at launch: about $15–35/month.** That is the whole point of these choices.

> ⚠️ **Vercel Hobby forbids commercial use.** The moment you charge anyone money, you need Vercel Pro at $20/month. Budget for it. Don't get your project pulled down the week you get your first paying customer.

> 💡 **DigitalOcean credits:** if you meant DigitalOcean ("blue ocean"), the GitHub Student Developer Pack gives $200 for a year. That covers the backend and database for the entire build. Use App Platform (it takes a Dockerfile and gives you HTTPS) rather than a bare droplet — you do not want to be configuring nginx in week 3.

---

## Repo shape

Restructure in week 1. Doing it later is much more painful.

```
/
├── apps/
│   ├── web/              Next.js — landing, dashboard, /s/, /a/
│   └── api/              FastAPI — everything above
├── packages/
│   └── specs/            The JSON spec schemas. THE most important folder.
├── docker-compose.yml    Local dev: api + postgres + redis
├── PRODUCT.md
├── BUILD_PLAN.md
└── MODULES.md
```

**`packages/specs/` is the contract.** Pydantic models on the Python side, TypeScript types generated from them for the frontend. One source of truth. If the spec drifts between frontend and backend, you will spend days on bugs that make no sense.

---

## Deployment, set up once in week 1

Do not leave this to the end. Get a real URL live in the first two days, even if it says "coming soon."

```
git push to main
   ├──→ Vercel sees apps/web/  → builds → deploys → ourdomain.com
   └──→ Render sees apps/api/  → builds Dockerfile → deploys → api.ourdomain.com
```

Concretely:

1. Buy the domain.
2. Create Supabase project (Mumbai/Singapore). Save the connection string.
3. `apps/api/Dockerfile` — python:3.11-slim, `uv sync`, `uvicorn`. Nothing fancy.
4. `docker-compose.yml` for local: api + postgres + redis. One command to start working.
5. Connect the repo to Vercel and Render. Point at the right subfolders.
6. Set environment variables in both dashboards — never in the repo.
7. Push a "coming soon" page. **Confirm it loads on your phone over mobile data.**

Two environments only: `main` → production, and local. A staging environment is a luxury you cannot afford at 20 days, and Vercel gives you a preview URL per pull request anyway.

### Migrations

Use **Alembic** from the very first table. Not "later." The first time you change a column on a database that has a real user's data in it, you will be glad.

---

## Week by week

### Weeks 1–2 · Foundation (5 days)
*Modules 1, 2, 3*

Boring, unglamorous, and the whole thing rests on it.

- Repo restructure, Docker, docker-compose, Alembic
- Domain bought, Vercel + Render connected, "coming soon" live
- Database tables: `users`, `apps`, `specs`, `records`, `app_users`, `workflow_runs`, `usage`
- Google sign-in working end to end
- Dashboard shell: sidebar, "New Website" / "New App", empty states
- Spec schemas written in Pydantic, TS types generated

**Done when:** you can sign in with Google on the real domain and land on an empty dashboard.

---

### Weeks 3–4 · Ship the Website Builder (5 days)
*Modules 4, 5, 10 → **LAUNCH v0.1***

- 4–5 hand-built site templates (portfolio, freelancer, small business, event, personal). Hand-build them properly — they are your quality ceiling.
- Site spec schema + the AI call that fills it
- Prompt → plan → build → preview → publish flow
- Publish layer: spec → cached Redis → server-rendered at `/s/<slug>`
- Landing page that actually explains the product, with pricing
- Sentry, basic analytics (Plausible or Vercel Analytics)

**Then launch.** Post it. Reddit (r/SideProject, r/IndiaStartups), Twitter/X, LinkedIn, Peerlist, your college groups, local business WhatsApp groups. Target: **30 signups, 10 published sites.**

Talk to every single one of those ten people. Ask what they actually do at work every day that is annoying. That conversation is worth more than another feature.

**Done when:** a stranger published a site and you did not touch anything.

---

### Weeks 5–6 · The runtime (5 days)
*Modules 6, 7, 8 — the hardest stretch in the plan*

Build in this order, and **write the specs by hand.** No AI yet.

1. **Renderer** — read an app spec, draw the pages. Form, table, record detail, nav.
2. **Record API** — create/read/update, every query scoped by `app_id`, enforced server-side.
3. **App-user login** — email + password, separate session, roles and permissions.
4. **Workflow engine** — walk the steps, evaluate conditions, pause at approvals, resume, log every step.
5. **Notifications** — in-app bell + email via Resend.

**Do not move on until this works:** hand-write the leave management spec, then submit a request as an employee, approve it as a manager, see the record change, see the notification arrive. Then do the same for expense claims (tests the numeric conditions) and complaints (tests branching).

This is milestone that decides whether the project succeeds. If the runtime is shaky, the AI on top of it is worthless.

---

### Week 7 · The AI layer (2.5 days)
*Module 9*

Now that there is something to generate *for*, this part is small.

- Planner: description → app spec + workflow spec
- Validator: reject anything outside the block catalog, retry once with the errors fed back in
- Plan screen: show it in plain English, let the user edit before building
- Test runner: execute a workflow with fake data, show each step tick off
- Natural-language edit: "add HR approval if over 7 days" → show the diff → Apply / Cancel

Test the planner against 20 descriptions you write yourself before you let anyone else near it. Count how many produce a valid, sensible spec. Under 80%, fix the prompt and the catalog, not the model.

---

### Week 8 · Polish and launch v0.2 (2.5 days)
*Module 11 + launch*

- Three templates (leave, expenses, complaints) as one-click starts
- Usage limits and counters — the free tier has to actually be enforced
- Onboarding: a 60-second guided first build
- Empty states, loading states, error messages a non-developer can read
- Load-test one published app. Fix the slowest query.
- Update the landing page. Record a 90-second demo video.
- **Launch.** Product Hunt, Hacker News (Show HN), the same channels as v0.1, plus back to every v0.1 user personally.

---

## If you fall behind

You will. Cut in this order — first to go at the top:

1. Natural-language editing (Module 9) — ship a plain edit form instead
2. Email notifications — in-app only is enough to demo
3. The `ai.classify` step — drop the complaints demo
4. Dashboard screen type — a table does the job
5. Usage limits — trust your first 50 users, count usage silently

**Never cut:** server-side tenant isolation, the validator, the test runner. The first is a security hole, the second lets bad specs reach users, and the third is the feature that makes people trust the output.

---

## Rules to work by

**Every session, before you start:** pick the one thing that most reduces the risk of the whole project failing. Do that. Not the fun thing.

- **Deploy on day one, deploy every week.** Never let "it works locally" be the state of things for more than a few days.
- **Hand-write the spec before you generate it.** Every time, for every feature.
- **The validator is the product.** An invalid spec must never reach a user.
- **`app_id` on every query.** Write a helper that makes it impossible to forget, and never query the records table directly.
- **Never publish generated JavaScript to your own domain.**
- **Log every workflow step.** A workflow you cannot see inside is a workflow you cannot support.
- **Write tests for the workflow engine only.** Skip tests everywhere else at this budget. The engine is where a silent bug costs you a customer.
- **Talk to a real user every week from week 4 onward.** Not optional.

---

## What could actually go wrong

| Risk | How likely | What to do about it |
|---|---|---|
| Weeks 5–6 overrun | **High** | It is 5 days for the hardest work in the plan. Cut the dashboard screen type and email notifications first. Protect the engine. |
| Planner output is unreliable | Medium | Smaller block catalog, more examples in the prompt, always show the plan for approval. If Sonnet still struggles, try Opus 5 before blaming the design. |
| Nobody signs up at v0.1 | Medium | That is exactly why v0.1 exists at week 4 and not week 8. You get four weeks to change the pitch. |
| Published apps feel slow | Low | Cache specs in Redis, one region, paid always-on backend. All three are already in the plan. |
| Tenant data leak | Low but fatal | One helper for all record access. Turn on Postgres row-level security as a second net. |
| You burn out | Real | 2–3 days a week is a marathon pace. The week-4 launch gives you a win at the halfway point. That is deliberate. |
