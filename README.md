# G4T4-IS213

## FeastFinder
<p align="center">
  <img alt="FeastFinder Demo" src="./FeastFinder_Demo.gif" width="800" />
</p>

Restaurant table booking with waitlist reallocation and delivery.

## Problem Statement

Restaurants face significant revenue loss due to last-minute cancellations, inefficient seat allocation, and high delivery platform commissions. There is a need for an integrated reservation and delivery management system for restaurants.

## Prerequisites

Ensure you have the following installed:

- [Node.js](https://nodejs.org/) (v16 or newer recommended)
- npm (comes with Node.js)
- [GitHub Desktop](https://desktop.github.com/) or Git CLI
- Docker
- IDE (any)


## Getting Started

There are two ways to run FeastFinder locally. **Option A (Dev)** is what you want
unless you are specifically testing the production deployment.

---

### Option A: Development Mode — Vite Hot-Module-Reloading

Runs Supabase, 17 microservices, Kong Gateway, RabbitMQ, and the frontend as a live
Vite dev server. Edit a file and the browser updates without a rebuild.

```bash
# 1. Clone
git clone https://github.com/WeiShenL/G4T4-IS213.git
cd G4T4-IS213

# 2. Seed the env files — the defaults are already set for dev, no edits needed
cp .env.example .env                    # Supabase/Postgres config + Compose interpolation
cp backend/.env.example backend/.env    # microservice runtime config
cp frontend/.env.example frontend/.env  # browser client config

# 3. Start
docker compose up -d
```

Open **[http://localhost:8080](http://localhost:8080)**. That's it.

> Stripe and Google Maps keys are left as placeholders in `frontend/.env` — the app
> boots and browses fine without them; only checkout and the map views need real ones.

> Vite is also exposed directly on [http://localhost:5173](http://localhost:5173), but
> prefer `:8080`. Both serve the same container and both hot-reload — only `:8080` goes
> through the gateway that routes `/api/*`, `/auth/*` and `/rest/*` to the backend, so
> on `:5173` every API call 404s.

Stop with `docker compose down`.

---

### Option B: Production Mode, Run Locally (Zero-Trust Hardened Caddy Edge)

Runs exactly what the VPS runs: the frontend as a multi-stage static Caddy build with
no Node.js runtime, and **no host ports on anything**. Because nothing is published to
`localhost`, you need the shared edge proxy in front of it — so this stack goes up
*second*, after the proxy.

**Step 1 — Clone and start the local edge proxy** ([vps-infra-portfolio](https://github.com/WeiShenL/vps-infra-portfolio)):

```bash
git clone https://github.com/WeiShenL/vps-infra-portfolio.git
cd vps-infra-portfolio
docker compose -f docker-compose.local.yaml up -d
```

This starts a root Caddy on host port `8080` and **creates the shared `web-gateway`
Docker network** that the app stack attaches to. No separate `docker network create`
is needed.

**Step 2 — Point the frontend at the Option B origin.**

In `frontend/.env`, comment out the two `localhost:8080` lines and uncomment the two
`feast.localhost:8080` lines directly beneath them. Both are already in the file with
instructions — you are just flipping which pair is active.

These are baked into the bundle at build time and must match the URL in your address
bar exactly, or you get CORS origin errors (a misleading symptom — it looks like the
backend is down, not misconfigured).

**Step 3 — Start FeastFinder in production mode:**

```bash
cd ../G4T4-IS213          # clone it first if you haven't (see Option A step 1)
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d
```

**Step 4 — Browse [http://feast.localhost:8080](http://feast.localhost:8080)**

Browsers resolve `*.localhost` to `127.0.0.1` on their own, so there is no `/etc/hosts`
edit to make. The request goes: browser → root Caddy (`:8080`) → `g4t4-caddy` → the
stack, which is the same proxy hop the VPS performs.

> **Do not add `--build`.** Without it, compose reuses a local image if present, pulls
> from GHCR if not, and only compiles from source when the pull fails — which is what
> happens on Apple Silicon, since the published images are `linux/amd64` only. The same
> command runs unchanged on the VPS. See "How images are named" in `STARTUP.md`.

> **Don't run Option A and Option B at the same time.** Both want host port `8080` — in
> dev it's `g4t4-caddy` directly, in prod it's the root Caddy. `docker compose down`
> the other one first.

To check the stack without a browser:

```bash
docker run --rm --network web-gateway curlimages/curl:latest \
  -s -o /dev/null -w '%{http_code}\n' http://g4t4-caddy/
```

On the VPS the same stack is served at `https://feast.weishenlo.com` via the root Caddy.

---

### Access Points
| Service | Option A — Dev | Option B — Prod (local) |
|:---|:---|:---|
| **Unified Single Entrypoint** | **http://localhost:8080** | **http://feast.localhost:8080** (via root Caddy) |
| Vite dev server (direct, no API) | http://localhost:5173 | n/a — static build, no dev server |
| Kong API Gateway | Internal Proxy (`/api/*`) | internal only (`!reset []`) |
| Supabase Auth & REST | Internal Proxy (`/auth/*`, `/rest/*`) | internal only (`!reset []`) |
| Supabase Studio | http://localhost:3000 | disabled (`replicas: 0`) |
| RabbitMQ Console | http://localhost:15672 (guest/guest) | `127.0.0.1:15672` (loopback only) |

In production mode the only services with host bindings are `supabase-db`,
`kong-database`, `kong` (admin), and `rabbitmq` — all bound to `127.0.0.1` for
shell access, none publicly reachable. Everything else is reached over the
`web-gateway` network by the root Caddy.

### Stop All Services
```bash
# Option A — dev stack:
docker compose down

# Option B — production stack:
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml down

# ...and the local edge proxy, if you started it:
cd ../vps-infra-portfolio && docker compose -f docker-compose.local.yaml down
```
> Add `-v` to the FeastFinder commands to also wipe the database. You will need to
> re-run the env setup steps before the next `up`, since `POSTGRES_PASSWORD` is only
> applied when Postgres first creates its data directory.

## Technical Architecture Diagram
<img width="809" alt="Screenshot 2025-04-11 at 7 25 24 AM" src="https://github.com/user-attachments/assets/c41e08a8-5bb9-4c39-b9f0-4b1fe3d71d7e" />

## Frameworks and Databases Utilised
<p align="center"><strong>Microservices and UI</strong></p>
<p align="center">
<a href="https://vitejs.dev/"><img src="https://upload.wikimedia.org/wikipedia/commons/f/f1/Vitejs-logo.svg" alt="Vite" height="40"/></a>&nbsp;&nbsp;
<a href="https://vuejs.org/"><img src="https://upload.wikimedia.org/wikipedia/commons/9/95/Vue.js_Logo_2.svg" alt="Vue" height="40"/></a>&nbsp;&nbsp;
<a href="https://developer.mozilla.org/en-US/docs/Web/JavaScript"><img src="https://upload.wikimedia.org/wikipedia/commons/6/6a/JavaScript-logo.png" alt="JavaScript" height="40"/></a>&nbsp;&nbsp;
<a href="https://www.python.org/"><img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" alt="Python" height="40"/></a>&nbsp;&nbsp;
<a href="https://flask.palletsprojects.com/"><img src="https://upload.wikimedia.org/wikipedia/commons/3/3c/Flask_logo.svg" alt="Flask" width="100"/></a>&nbsp;&nbsp;
<a href="https://supabase.com/"><img src="https://www.vectorlogo.zone/logos/supabase/supabase-icon.svg" alt="Supabase" height="55" /></a>&nbsp;&nbsp;
<br>
<i>Vite · Vue · JavaScript · Python · Flask · Supabase Auth</i>
</p>
<br>

<p align="center"><strong>Low Code Platform</strong></p>
<p align="center">
<a href="https://www.outsystems.com/"><img src="https://upload.wikimedia.org/wikipedia/commons/8/82/OS-logo-color_500x108.png" alt="outsystems" width="100"/></a>
<br>
<i>outsystems</i>
</p>
<br> 

<p align="center"><strong>External API</strong></p>  
<p align="center">
<a href="https://maps.google.com/"><img src="https://upload.wikimedia.org/wikipedia/commons/thumb/3/39/Google_Maps_icon_%282015-2020%29.svg/1280px-Google_Maps_icon_%282015-2020%29.svg.png" alt="Google Maps" height="40"/></a>&nbsp;&nbsp;
<a href="https://stripe.com/"><img src="https://upload.wikimedia.org/wikipedia/commons/thumb/b/ba/Stripe_Logo%2C_revised_2016.svg/1280px-Stripe_Logo%2C_revised_2016.svg.png" alt="Stripe" height="40"/></a>&nbsp;&nbsp;
<a href="https://resend.com/"><img src="https://cdn.resend.com/brand/resend-icon-black.svg" alt="Resend" height="40" /></a>&nbsp;&nbsp;
<a href="https://openstreetmap.com/"><img src="https://upload.wikimedia.org/wikipedia/commons/1/15/OpenStreetMap_icon_simple.svg" alt="Open Street Map" height="40"/></a>&nbsp;&nbsp;
<br>
<i>Google Maps API · Stripe · Resend Email · Open Street Map</i>
</p>
<br>

<p align="center"><strong>Storage Solutions</strong></p>  
<p align="center">
<a href="https://supabase.com/"><img src="https://www.vectorlogo.zone/logos/supabase/supabase-icon.svg" alt="Supabase" height="55" /></a>&nbsp;&nbsp;
<br>
<i>Supabase</i>
</p>
<br> 

<p align="center"><strong>Message Brokers</strong></p>
<p align="center">
<a href="https://www.rabbitmq.com/"><img src="https://upload.wikimedia.org/wikipedia/commons/7/71/RabbitMQ_logo.svg" alt="RabbitMQ" width="100"/></a>
<br>
<i>rabbitMQ</i>
</p>
<br> 

<p align="center"><strong>Inter-service Communications</strong></p>
<p align="center">
<a href="https://restfulapi.net/"><img src="https://keenethics.com/wp-content/uploads/2022/01/rest-api-1.svg" alt="REST API" height="40"/></a>
<br>
<i>REST API</i>
</p> 
<br>

<p align="center"><strong>API Gateway</strong></p>
<p align="center">
<a href="https://konghq.com/"><img src="https://avatars.githubusercontent.com/u/962416?s=280&v=4" alt="Kong API Gateway" width="88"/></a>
<br>
<i>Kong</i>
</p>
<br> 

<p align="center"><strong>Deployment & Containerization</strong></p>
<p align="center">
<a href="https://github.com/"><img src="https://avatars.githubusercontent.com/u/44036562?s=280&v=4" alt="GitHub Actions" height="60"/></a>&nbsp;&nbsp;
<a href="https://www.docker.com/"><img src="https://upload.wikimedia.org/wikipedia/commons/4/4e/Docker_%28container_engine%29_logo.svg" alt="Docker" height="30"/></a>&nbsp;&nbsp;
<a href="https://containrrr.dev/watchtower/"><img src="https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/watchtower.png" alt="Watchtower" height="40"/></a>&nbsp;&nbsp;
<a href="https://caddyserver.com/"><img src="https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/caddy.png" alt="Caddy" height="40"/></a>&nbsp;&nbsp;
</p>
<p align="center">
<i>Github Actions· Docker Compose · Watchtower · Caddy</i>
</p>
<br> 

> [!NOTE]
> **Submitted Project Snapshot:** The original project submission for evaluation is preserved in the [`submitted-project`](https://github.com/WeiShenL/G4T4-IS213/tree/submitted-project) branch (`git checkout submitted-project`).
> 
> **Post Submission Improvements:**
> - **Local Self-Hosted Supabase**: Full Docker setup with Supabase Realtime for live order & driver dashboard updates.
> - **Real-Time Live Dashboards**: Instant WebSocket updates via Supabase Realtime for Customer & Driver dashboards (no manual page refreshes needed).
> - **Native Waitlist Microservice**: Replaced OutSystems with custom Python microservice & decline reallocation workflow.
> - **Resend Email Service**: Integrated Resend API for transactional notifications, instead of paid Twilio SMS API.
> - **Production VPC Ready**: Docker containerization, including Frontend and Backend for both local and prod environments. WatchTower will be used to fetch latest push to main to update containers for production.