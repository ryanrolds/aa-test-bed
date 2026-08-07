# wanderer-aa

An **Alliance Auth test bed** for developing Alliance Auth plugins, running
alongside a live [Wanderer](https://github.com/wanderer-industries/wanderer)
instance so integration plugins can be built and exercised end to end.

The first plugin exercised here is
[`aa-wanderer-leaderboard`](https://github.com/ryanrolds/aa-wanderer-leaderboard)
— an Alliance Auth leaderboard for Wanderer. It is installed from
[PyPI](https://pypi.org/project/aa-wanderer-leaderboard/); its source lives in
its own repo.

Everything runs from a single Docker Compose project.

## What's in the box

| Stack | Services | Host URL |
| --- | --- | --- |
| **Wanderer** | `wanderer`, `wanderer_db` (Postgres), `eve-route-builder`, `wanderer-kills` | http://localhost:8000 |
| **Alliance Auth** | `allianceauth_init` (one-shot: migrate + collectstatic), `allianceauth_gunicorn`, `allianceauth_worker`, `allianceauth_worker_services`, `allianceauth_beat`, `aa_nginx`, `aa_mysql` (MariaDB), `aa_redis` (Redis) | http://localhost:8001 |

The two stacks are independent (separate databases and networks); they share the
`wanderer-egress` bridge so the AA plugin can reach the Wanderer service by name
(`http://wanderer:8000`).

Alliance Auth version is pinned via `AA_DOCKER_TAG` in `.env` (currently `v5.2.0`).

## Prerequisites

- Docker + Docker Compose v2
- Two EVE SSO applications (one already exists for Wanderer) from
  <https://developers.eveonline.com> — see below.

## First-time setup

### 1. Configuration & secrets

`.env` (compose interpolation + AA runtime config) and `wanderer-conf.env`
(Wanderer app config) are git-ignored and already contain generated secrets for
local use. If you're starting from a clean checkout, copy the example and
generate fresh values:

```bash
cp .env.example .env
# then generate and paste in:
openssl rand -base64 48   # AA_SECRET_KEY
openssl rand -hex 16      # AA_DB_PASSWORD, AA_DB_ROOT_PASSWORD, POSTGRES_PASSWORD
```

### 2. EVE SSO application for Alliance Auth

Create a **new** application at <https://developers.eveonline.com> (separate from
the Wanderer app):

- **Callback URL:** `http://localhost:8001/sso/callback` (must match `AA_SITE_URL` exactly)
- **Scopes:** `publicData` to start (AA requests more per service as needed)

Put the client ID/secret into `.env`:

```
ESI_SSO_CLIENT_ID=...
ESI_SSO_CLIENT_SECRET=...
ESI_USER_CONTACT_EMAIL=you@example.com
```

### 3. Start everything

```bash
docker compose up -d --build
```

The AA app image is built on top of the published AA image and installs the
plugins pinned in [`conf/aa/requirements.txt`](conf/aa/requirements.txt) from
PyPI.

Migrations and static files are handled automatically: the one-shot
`allianceauth_init` service waits for `aa_mysql` to report healthy, applies AA
core + plugin migrations, runs `collectstatic` into the `aa-static` volume that
`aa_nginx` serves, and exits — the app services only start once it succeeds.
Both steps are idempotent, so it runs on every `up` and is a no-op when the
schema and static files are current.

### 4. Create an admin user (first run only)

```bash
docker compose exec -it allianceauth_gunicorn python manage.py createsuperuser
```

User portals:
* Alliance Auth - http://localhost:8001
* Wanderer - http://localhost:8000

Admin portals:
* http://localhost:8001/admin/
* http://localhost:8000/admin/

> Grant your user the plugin's permission at
> **Admin → Authentication and Authorization → Users** (or via a group):
> `wanderer_leaderboard | general | Can access the Wanderer Leaderboard`. The
> **Wanderer Leaderboard** menu item appears once granted.

### 5. Wanderer Leaderboard: map API key

The leaderboard reads Wanderer's audit API (`GET /api/map/audit`), authenticated
per map with that map's own API key — no database access, no Postgres role.

1. In Wanderer (http://localhost:8000), open the map's settings and copy its
   **API key**.
2. In AA admin → **Wanderer Leaderboard → Tracked maps**, add a map with its
   slug (or map id) and paste the key into **API key**. Leave **base URL** blank
   to use the compose default (`http://wanderer:8000`).
3. Select the map in the list and run the **Test the API key against Wanderer**
   admin action to confirm it works before relying on it.

Then open **http://localhost:8001/wanderer-leaderboard/**.

> The audit API only serves *relative* windows (max `3M`), so the leaderboard
> pulls three months and slices the selected month out locally. Months older
> than that can't be retrieved and render an explanatory notice. Responses are
> cached for `WANDERER_LEADERBOARD_CACHE_TTL` seconds (default 300).

## Plugin workflow

Plugins are installed from PyPI, pinned in
[`conf/aa/requirements.txt`](conf/aa/requirements.txt). The source for
`aa-wanderer-leaderboard` lives in
[its own repo](https://github.com/ryanrolds/aa-wanderer-leaderboard).

- **Test a new plugin release** → bump the pin and rebuild. Any new migrations
  are applied by `allianceauth_init` on the way up:
  ```bash
  docker compose up -d --build
  ```
- **Test unreleased plugin code** → point the requirement at a git ref instead
  of a version, then rebuild as above:
  ```
  aa-wanderer-leaderboard @ git+https://github.com/ryanrolds/aa-wanderer-leaderboard@main
  ```
  (`--build` alone may reuse the cached layer for an unchanged URL; use
  `docker compose build --no-cache allianceauth_gunicorn` to force a re-pull.)
- **Add another plugin or dependency** → add it to
  [`conf/aa/requirements.txt`](conf/aa/requirements.txt) and rebuild:
  ```bash
  docker compose up -d --build
  ```
- **Register a new plugin app** in INSTALLED_APPS via
  [`conf/aa/local.py`](conf/aa/local.py).
- **Edit `conf/aa/local.py`** (settings, Celery schedule, INSTALLED_APPS) →
  `restart` fails on this Docker Desktop/WSL setup because editing a mounted file
  invalidates the container's cached mount. Use `up -d` to **recreate** instead:
  ```bash
  docker compose up -d allianceauth_gunicorn allianceauth_worker allianceauth_worker_services allianceauth_beat
  ```
  (`aa_nginx` re-resolves the gunicorn upstream via Docker DNS, so recreating the
  app no longer requires restarting nginx.)

## Layout

```
docker-compose.yml        Wanderer + Alliance Auth services (merged)
.env                      secrets + config (git-ignored)
wanderer-conf.env         Wanderer app config (git-ignored)
conf/aa/
  Dockerfile              builds the AA image (installs the pinned plugins)
  local.py                AA settings override (DB, redis, ESI, plugins)
  celery.py               AA celery app
  nginx.conf              static files + reverse proxy for AA
  requirements.txt        pinned plugins/pip packages for the AA image
```

## Useful commands

```bash
docker compose ps                              # status
docker compose logs -f allianceauth_gunicorn   # AA web logs
docker compose exec allianceauth_gunicorn bash # shell in the AA container
docker compose down                            # stop (keeps volumes/data)
docker compose down -v                         # stop and DELETE all data
```
