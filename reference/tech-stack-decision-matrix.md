# Tech Stack Decision Matrix

Scoring framework for selecting the right technology stack during Phase 3 (Recommend). Use the app analysis from Phase 1 and discovery answers from Phase 2 to score each option.

## Guiding Philosophy

**The default is a full-stack MVC monolith.**

Server-side MVC frameworks — Django, Laravel, Rails — are not a compromise. They are the architecture behind Shopify (Rails, $14.6B Black Friday 2025), GitHub (Rails), Instagram (Django, 30M users with 3 engineers), and Pinterest (Django, 200B pins). These are not small applications making do with limited technology. They are proof that server-side MVC has no practical ceiling.

FileMaker itself is a monolith. Replacing it with a separate frontend + backend API introduces two codebases that must agree on data shapes, auth flows, error formats, and validation — on both sides. Every database column change ripples through the serializer, TypeScript interface, form component, and validation logic twice. A full-stack MVC framework keeps all of that in one place.

**Only recommend a separate frontend when the user has a documented, specific need that the MVC framework cannot satisfy.**

## How to Use This Matrix

1. Read the app complexity score and feature map from Phase 1
2. Read the user's preferences and constraints from Phase 2
3. **The first branch is coding mode — AI or human.** That determines everything downstream.
4. For the human/hybrid path, use WebSearch to pull current data before recommending. Do not rely on training knowledge alone — framework ecosystems move. Show the user what you found and let them decide.

---

## Database Layer

### Candidates

| Criteria | PostgreSQL | MySQL | SQLite |
|---|---|---|---|
| **Complex queries** (joins, CTEs, window functions) | Excellent | Good | Limited |
| **JSON support** (if FM used flexible schemas) | Excellent (JSONB) | Good (JSON type) | Basic |
| **Full-text search** | Built-in (tsvector) | Built-in (FULLTEXT) | Extension (FTS5) |
| **Row-level security** | Built-in (RLS policies) | No | No |
| **Concurrent users >10** | Excellent (MVCC) | Good | Poor (file locking) |
| **Stored procedures / triggers** | Excellent | Good | Limited |
| **Hosting availability** | Universal | Universal | Embedded only |
| **Ease of setup** | Moderate | Moderate | Trivial |
| **Scaling ceiling** | Very high | High | Low |

### Selection Guide

- **PostgreSQL** — Default recommendation for most FM migrations. Handles FM's complex relationships, supports RLS for privilege set mapping, excellent for 5+ concurrent users.
- **MySQL** — Choose if the team already uses MySQL, or if the hosting environment requires it.
- **SQLite** — Only for very simple apps (<5 tables, <3 users, no concurrent writes). Good for prototyping.

---

## Full-Stack Framework (The Primary Decision)

This is the most important choice. The right answer depends first on **who is writing the code**.

---

### Path A — AI / Vibe-Coded

AI-generated code excels with full-stack MVC frameworks. There is one obvious way to do everything: one ORM, one migration command, one auth library, one admin panel. AI doesn't have to choose between Redux and Zustand, or decide whether to put data fetching in `useEffect` or `useQuery`. It just follows the framework's conventions.

AI-generated React code almost universally misuses `useEffect`, optimistic updates, and client-side cache invalidation — producing apps that pass development but fail in production.

**For AI-coded projects, go straight to the MVC giants:**

| Framework | Language | Built-In | Admin Panel | Background Jobs |
|---|---|---|---|---|
| **Django** | Python | Auth, ORM, migrations, email, testing | `django.contrib.admin` — auto-generated from models | Celery (add-on, near-universal) |
| **Laravel** | PHP | Auth (Breeze/Jetstream), ORM (Eloquent), migrations, email, queues | Filament (free/OSS) or Nova | Laravel Queues (built-in) |
| **Rails** | Ruby | Auth (Devise gem), ORM (ActiveRecord), migrations, email, jobs (Sidekiq) | ActiveAdmin or Avo | Active Job + Sidekiq |

All three require 2–3 decisions before feature work begins. A React SPA requires 12–15+.

**Selection for AI path:** match team language. If no preference, default to Django — Python is the most broadly known language and Django's explicit conventions produce consistent AI output.

---

### Path B — Human / Hybrid

Ask the team what language they write. Then **use WebSearch** to pull current, real-world data before recommending anything. Do not rely on training knowledge — framework ecosystems shift. Search for:

- `"[language] web framework 2025 production"`
- `"[framework A] vs [framework B] 2025"`
- Stack Overflow Developer Survey results for that language
- GitHub star trajectory and recent commit activity for the top candidates

Present what you find in plain language: community size, production adoption, recent momentum, any notable concerns (maintenance risk, breaking changes, corporate backing changes). Let the user weigh in. The goal is that they feel like they researched this and made an informed decision — not that they accepted a default.

**After presenting findings, apply the same MVC-first filter:** among the well-supported options for their language, prefer the full-stack MVC framework over the API-only microframework. A well-maintained full-stack framework beats a bare API framework every time for this class of application.

---

### Interactivity Without a Separate Frontend

### Interactivity Without a Separate Frontend

You do not need React to build an interactive, modern web UI. These tools add reactivity to server-rendered MVC apps:

| Tool | Framework | What It Does |
|---|---|---|
| **Hotwire (Turbo + Stimulus)** | Rails | HTML-over-the-wire. Partial page updates, real-time via ActionCable. The Rails default. |
| **Livewire** | Laravel | Server-driven reactive components. Write PHP, get real-time UI. |
| **HTMX** | Any (great with Django) | HTML attributes that trigger AJAX requests. No build step. No state management. |
| **Alpine.js** | Any | Lightweight JS for local UI state (dropdowns, modals). Declarative. No bundler. |

These eliminate the state synchronization problem entirely. Every request hits the database. There is no client-side cache to go stale, no optimistic update to conflict, no `useEffect` dependency array to get wrong.

---

## When a Separate Frontend Is Justified (The Exception)

A separate React/Vue/Svelte frontend is appropriate **only** when one or more of the following is true and documented in the discovery answers:

| Condition | Why It Justifies a Separate Frontend |
|---|---|
| **Native mobile app** (iOS/Android) is required | Mobile apps need a JSON API. If you're building a native app, you need the API anyway. |
| **Real-time collaborative editing** (Google Docs-style) | WebSocket-heavy, conflict-resolution-heavy. SPA patterns are genuinely better here. |
| **Offline-first PWA with local sync** | Requires client-side state and sync logic that server rendering cannot provide. |
| **Existing team is deeply invested in React/Vue** | They built in React before, they know it well, retraining cost is high. Accept it — but document the tradeoff. |
| **Public-facing, SEO-critical marketing site** | Use a static site generator (Astro, Hugo), not React. |

If none of these apply, the default stands: full-stack MVC with server-rendered templates.

### If a Separate Frontend Is Justified

| Criteria | React | Vue | Svelte |
|---|---|---|---|
| **Ecosystem depth** | Largest | Large | Growing |
| **Learning curve** | Moderate | Low | Low |
| **State management complexity** | High (Redux/Zustand/React Query) | Moderate (Pinia) | Low (built-in stores) |
| **AI-generated code quality** | Poor (useEffect misuse is near-universal) | Moderate | Good |
| **Long-term maintenance** | High burden | Moderate burden | Lower burden |

**Selection Guide:**
- If the team already knows React → accept it, but enforce React Query (not raw useEffect for data fetching), strict TypeScript, and a state management discipline from day one.
- If no preference → **Vue** or **Svelte**. Lower state management burden, gentler learning curve, less ecosystem churn.
- Never use React because it is the "default" answer. That is JavaScript fatigue in action.

### CSS / Component Library (for Separate Frontend Only)

| Option | Best For | Notes |
|---|---|---|
| **Tailwind CSS** | Utility-first, custom designs | Most flexible. Good for teams that want control. |
| **shadcn/ui** (React) | Modern component library | Pre-built components with Tailwind. |
| **Vuetify** (Vue) | Material Design components | Rich component set for Vue. |
| **DaisyUI** | Tailwind component layer | Framework-agnostic. Works with any SSR or SPA. |
| **Bootstrap** | Quick, conventional UI | Familiar to most devs. Closest to FM's built-in themes. |

---

## Authentication

| Option | Best For | Complexity |
|---|---|---|
| **Framework built-in** (Django auth, Laravel Breeze, Devise) | MVC monolith apps — always try this first | Very Low |
| **Session-based (cookie)** | Server-rendered apps, simple auth | Low |
| **JWT tokens** | API-first apps with a mobile client | Moderate — avoid for browser-only apps |
| **OAuth2 / OpenID Connect** | Apps needing SSO or Active Directory login | Moderate |
| **Auth service** (Auth0, Clerk) | Teams that want managed auth and accept the SaaS cost | Very Low (but ongoing cost) |

### Selection Guide

- **MVC monolith default:** use the framework's built-in auth. Django auth, Laravel Breeze, or Devise cover every FM privilege set pattern.
- FM apps using Active Directory → **OAuth2/OIDC** via the MVC framework's OAuth library (django-allauth, Laravel Socialite).
- JWT is appropriate only if you have a mobile app or a third-party client consuming your API. Do not use JWT for browser-only sessions — cookies are simpler, more secure, and the framework already handles them.

---

## Deployment

| Option | Best For | Cost | Ops Effort |
|---|---|---|---|
| **PaaS** (Railway, Render, Fly.io) | Small teams, fast deployment | $5–50/mo | Very Low |
| **VPS** (DigitalOcean, Linode) | Budget-conscious, full control | $5–20/mo | Moderate |
| **Docker on VPS** | Reproducible deploys, moderate scale | $10–40/mo | Moderate |
| **AWS / GCP / Azure** | Enterprise, high scale, compliance | Variable | High |
| **On-premise** | Regulatory requirements, existing infra | Hardware cost | High |

### Selection Guide

- Default: **PaaS (Railway or Render)** — easiest migration from FM Server's operational model. Long-running server process. No serverless cold-start surprises.
- If the user runs FM Server on-premise and wants to stay on-premise → **Docker on existing server**.
- If cloud cost is a concern → **VPS with Docker**.
- Avoid Vercel/Netlify for MVC apps — they are optimized for static sites and serverless functions, not long-running processes. The billing model punishes traditional server apps.

---

## Architecture Pattern

| Pattern | When to Use | FM Complexity | Team Size |
|---|---|---|---|
| **Monolith** | Simple to medium apps, single domain | Simple–Medium | 1–3 |
| **Modular Monolith** | Clear domain boundaries, single deployment | Medium–Complex | 1–5 |
| **Microservices** | Independent scaling, multiple teams | Enterprise | 5+ |

### Default Recommendation

**Monolith or Modular Monolith** for most FileMaker migrations. FileMaker solutions are inherently single-application systems. They have clear domain boundaries (script groups map to modules), and their operational model (FM Server = one process, one database) maps naturally to a monolith deployment.

Monolith is underrated. Shopify is a monolith. GitHub is a monolith. Basecamp is a monolith. The people who say "you'll need microservices later" are almost never right, and the cost of premature distribution is high.

Only recommend microservices if the user explicitly has multiple teams, independent scaling requirements, or regulatory boundaries that require service isolation.

---

## Quick Decision Flowchart

```
Who is writing this?
│
├── AI / Vibe-coded
│     Need real-time collab or native mobile?
│     ├── No → Full-Stack MVC Giant. Match team language:
│     │         Python → Django + PostgreSQL + HTMX/Alpine + Django auth + PaaS
│     │         PHP    → Laravel + PostgreSQL + Livewire/Alpine + Breeze + PaaS
│     │         Ruby   → Rails + PostgreSQL + Hotwire + Devise + PaaS
│     │         None   → Django + PostgreSQL + HTMX/Alpine + Django auth + PaaS
│     └── Yes → MVC API backend + document what justified a separate frontend
│
└── Human / Hybrid
      What language does the team write?
      → WebSearch: "[language] web framework 2025 production"
      → Present findings to user (community, adoption, momentum, risks)
      → User picks from informed options
      │
      Need real-time collab or native mobile?
      ├── No → Full-stack MVC framework in their language (prefer the giant)
      └── Yes → MVC API + separate frontend, document the justification
```
