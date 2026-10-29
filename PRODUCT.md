# Product Definition & Architecture

> Working name: **TBD** — pick one before you build the landing page (Module 10).
> Status: this replaces the broad brainstorm in `AI_No_Code_Application_Workflow_Builder_Project_Context.txt`. That file is the research. This file is the decision.

---

## 1. The one-line promise

**"Describe how your work happens. Get a working system with a link."**

Not a code generator. Not "AI builds your app." You describe a process in plain words, and you get a live system that collects requests, routes them to the right person, records the decision, and tells everyone what happened.

---

## 2. Who it is for (be narrow on purpose)

Teams of **5–50 people** who run their operations on WhatsApp, Excel and paper:

- clinics and diagnostic labs
- coaching institutes and schools
- design / marketing / CA agencies
- small factories and distributors
- retail chains with 2–10 outlets
- college clubs and student bodies

They are not developers. They will never open a terminal. They have a real process in their head and no way to put it in software.

### What actually hurts them

| Their words | The real problem |
|---|---|
| "Requests get lost in WhatsApp" | No queue, no owner |
| "I don't know who approved this" | No audit trail |
| "People keep asking me for status" | No visibility |
| "Excel sheet got overwritten" | No permissions |

---

## 3. The sharp wedge

Everything in the MVP is one shape:

```
INTAKE  →  ROUTE  →  APPROVE / ACT  →  RECORD  →  NOTIFY
```

A leave request, an expense claim, a customer complaint, a purchase order, a client request form — all the same four boxes with different labels. We build that shape extremely well and refuse everything else.

**We say yes to:** forms, tables, records, roles, approvals, conditions, notifications, logs, a shareable link.

**We say no to:** payments, chat, file-heavy workflows, dashboards with charts, mobile apps, integrations beyond email/webhook, anything needing custom code. (All of these are post-launch questions, not MVP ones.)

---

## 4. What we offer — two products, one account

### Product A — Website Builder (the front door)

Choose one of 20 polished starting points, or describe a fully custom site and get a React/TypeScript build with a live preview and version history.

- **Purpose:** low-risk, instant win. It is how strangers become signed-up users.
- The template path has 20 ready-made directions and controls for page sections, header/footer, calls to action, colors and cards.
- The custom path uses LangGraph planner, designer, builder, reviewer and build-check stages to write a React + TypeScript + Tailwind site from a detailed brief.
- Free forever. No credit card. This is marketing, not revenue.

### Product B — Workflow Builder (the real product)

Describe a process → get a running internal system with a link.

The flow the user sees:

1. **Describe** — "Employees request leave. Their manager approves. Employee gets told."
2. **Review the plan** — we show, in plain English, exactly what we will build: who the users are, what forms exist, what gets stored, what happens step by step. *(Later: estimated running cost.)*
3. **Build** — takes seconds, not minutes.
4. **Try it** — run a test request end to end and watch each step tick off.
5. **Fix it in words** — "Also need HR approval if leave is over 7 days."
6. **Publish** — you get `ourdomain.com/a/leave-acme`. Send it to your team. They log in and use it.

This is what people pay for, in small credit packs.

### Why the two belong together

They share the exact same machinery:

| Shared piece | Used by |
|---|---|
| Login and account | Both |
| Prompt → plan → build → preview → publish flow | Both |
| Publish layer (spec in database → renderer → public URL) | Both |
| Usage tracking and limits | Both |

Building the site builder first means the hardest boring parts (auth, hosting, publishing, a real domain, a real deploy pipeline) are already proven and live before the workflow engine is written.

---

## 5. The safety boundary

**Workflow models fill a typed form. Website code is a separate, constrained build artifact.**

```
Workflow: plain English → AI planner → typed AppSpec → validator → workflow runtime
Custom site: brief → LangGraph roles → React/TSX + CSS → fixed build tools → opaque-origin iframe
```

Workflow planning picks from a fixed menu of about fifteen building blocks. It cannot invent a block, write SQL, or call an API we did not allow. Custom website generation is intentionally isolated from that workflow runtime: it writes only `App.tsx` and `styles.css`, uses an import allowlist, and passes a fixed build check before preview.

**Why this matters:**

- **Predictable** — the same spec always behaves the same way.
- **Safe** — custom code is parsed by fixed build tools and runs only in a sandboxed browser frame, outside the platform origin.
- **Cheap** — one small AI call per build, not thousands of tokens of code.
- **Fixable** — a bug in a form is fixed once in the renderer, for every user at once.
- **Fast** — published pages load from a cached spec, not from an AI call.

Workflow apps remain typed, permissioned and auditable. Custom websites get the flexibility of generated code without sharing the workflow runtime's security boundary.

---

## 6. The building blocks (the whole menu)

Anything the AI produces is made of only these.

**Screens:** Form · Table · Record detail · Simple list

**Data:** Entity (a thing you store) · Field (text, number, date, choice, yes/no, long text) · Link between entities

**Workflow steps:** Trigger (form submitted) · Create record · Update record · Condition (if/else) · Approval (wait for a person) · Notify (in-app) · Notify (email) · AI classify (sort text into categories)

**People:** User · Role · Permission (who can see/do what)

That is it. Twelve months from now this list will be longer. For launch it is frozen.

---

## 7. How a generated app stores data

We do **not** create new database tables for each app. One table holds everything:

```
records
  id · app_id · entity_name · data (JSON) · created_by · created_at · updated_at
```

Every read and write is filtered by `app_id` on the server. No exceptions, no frontend filtering.

**Why:** no database migrations at runtime, no schema drift, no chance of one customer's app breaking another's. JSON columns with the right indexes handle thousands of records per app comfortably — far past anything our first 100 customers will need.

---

## 8. Two separate logins (do not mix these up)

| | Platform login | App login |
|---|---|---|
| Who | The person who builds apps (our customer) | The people who use a built app (their staff) |
| How | Google sign-in | Email + password |
| Where | `ourdomain.com/dashboard` | `ourdomain.com/a/<slug>` |
| Scope | Owns apps and sites | Belongs to one app, has one role in it |

A published app's users are completely separate accounts. Their session cookie is scoped to that app only.

---

## 9. System architecture

```
 ┌──────────────────────────────────────────────────────────┐
 │  Next.js on Vercel                                       │
 │                                                          │
 │  /                     landing, pricing (public, fast)    │
 │  /login                Google sign-in                     │
 │  /dashboard            build & manage your apps           │
 │  /s/<slug>             a published website  (cached)      │
 │  /a/<slug>             a published app      (live data)   │
 └───────────────────────────┬──────────────────────────────┘
                             │  HTTPS / JSON
 ┌───────────────────────────▼──────────────────────────────┐
 │  FastAPI in Docker (Render / Railway / DigitalOcean)      │
 │                                                          │
 │  Auth check        verify the login token                 │
 │  Spec API          save / load app + site specs           │
 │  Planner           plain English → JSON spec → validate   │
 │  Runtime API       read/write records, always by app_id    │
 │  Workflow engine   run steps, pause at approvals, log     │
 │  Notifier          in-app messages + email                │
 └──────┬──────────────────────┬─────────────────┬──────────┘
        │                      │                 │
 ┌──────▼───────┐    ┌─────────▼──────┐   ┌──────▼───────┐
 │  Postgres    │    │  Redis cache   │   │  Claude API  │
 │  (Supabase)  │    │  (Upstash)     │   │              │
 │  users,specs │    │  published     │   │  planner +   │
 │  records,logs│    │  specs, hot    │   │  classify    │
 └──────────────┘    └────────────────┘   └──────────────┘
```

### Keeping it fast

- Published **websites** are pure spec → HTML. Rendered on the edge and cached. Sub-100ms.
- Published **apps** need live data, but the *spec* is cached in Redis, so a page load is one database query for records, not two round trips plus a spec lookup.
- Everything in **one region** close to users (India → Mumbai/Singapore). Do not spread the database and backend across continents.
- **No free-tier backend that sleeps.** A cold start is 30 seconds and it will lose you the customer. Pay the $7/month.

---

## 10. AI: what we use and what it costs

One small module, swappable provider. You are on Groq today; move to Claude for reliable structured JSON output.

| Job | Model | Why |
|---|---|---|
| Plan a workflow app | `claude-sonnet-5` | $2 / $10 per million tokens. Good at strict JSON. Default choice. |
| Fill website content | `claude-haiku-4-5` | $1 / $5 per million. Simple job, cheapest tier. |
| `ai.classify` step inside a running app | `claude-haiku-4-5` | Runs often, must be cheap. |
| Fallback if plan quality disappoints | `claude-opus-5` | $5 / $25 per million. Only if Sonnet measurably fails. |

**Real cost per build:** roughly 4K tokens in, 2K out → about **₹2–3 per app generated**. With prompt caching on the fixed block catalog, closer to ₹1.

This is the number that makes the business work: you can give away 3 free builds per user and lose almost nothing.

---

## 11. Money (later, but design for it now)

| Plan | Price | What you get |
|---|---|---|
| Free | ₹0 | 1 published website, 1 published app, 50 workflow runs/month |
| Starter | ₹299/month | 3 apps, 1,000 runs/month, remove our badge |
| Credit pack | ₹99 | 500 extra runs, never expires |

Charge for **runs**, not for AI access. A run is a real business event — a leave request processed, a complaint routed. That is a number a shop owner understands.

Track token usage per generation from day one even though you show nothing. When you turn pricing on, you will already know your real margin.

---

## 12. What "done" looks like

The launch is real when a stranger can, without talking to you:

1. Land on the site and understand it in 10 seconds
2. Sign in with Google
3. Type a description of their approval process
4. Read a plan that is actually correct
5. Click Build and see it working
6. Run a test and watch the steps pass
7. Change something by typing a sentence
8. Publish and get a link
9. Send that link to a colleague
10. Have that colleague log in, submit a request, and have the first person approve it

If that chain holds up ten times with ten different people, you have a product.

---

## 13. Three demo apps that prove the architecture

Build all three yourself, by hand, before the AI exists. If one runtime can run all three, the design is right.

| Demo | Proves |
|---|---|
| **Leave requests** | Roles, form, approval, notification |
| **Expense claims** | Numeric conditions, multi-level approval (auto / manager / director) |
| **Customer complaints** | AI classification, branching, assignment, public intake form |

These also become your homepage examples and your one-click templates.

---

## 14. Things we are deliberately not building

Writing these down so you don't drift:

custom domains · charts and analytics · general-purpose drag-and-drop page designer · file uploads · payments · Slack/WhatsApp integration · mobile apps · team collaboration on one app · white-label · API for customers · self-hosting · templates marketplace · Kubernetes · per-customer servers

Every one of these is a reasonable thing to want. None of them is why someone will pay you the first ₹299.
