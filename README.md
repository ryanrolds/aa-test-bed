# wanderer-aa

An **Alliance Auth test bed** for developing Alliance Auth plugins, running
alongside a live [Wanderer](https://github.com/wanderer-industries/wanderer)
instance so integration plugins can be built and exercised end to end.

The first plugin under development is [`aa-wanderer`](plugins/wanderer) — an
Alliance Auth ↔ Wanderer integration.

Everything runs from a single Docker Compose project.

## What's in the box

| Stack | Services | Host URL |
| --- | --- | --- |
| **Wanderer** | `wanderer`, `wanderer_db` (Postgres), `eve-route-builder`, `wanderer-kills` | http://localhost:8000 |
| **Alliance Auth** | `allianceauth_gunicorn`, `allianceauth_worker`, `allianceauth_worker_services`, `allianceauth_beat`, `aa_nginx`, `aa_mysql` (MariaDB), `aa_redis` (Redis) | http://localhost:8001 |

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
local `plugins/wanderer` package in editable mode.

### 4. Initialize the Alliance Auth database (first run only)

```bash
docker compose exec allianceauth_gunicorn python manage.py migrate
docker compose exec allianceauth_gunicorn python manage.py collectstatic --noinput
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
> `wanderer | general | Can access the Wanderer integration`. The **Wanderer**
> menu item appears once granted.

## Plugin development workflow

The plugin lives in [`plugins/wanderer/`](plugins/wanderer) and is bind-mounted
into the AA containers, so the loop is fast:

- **Edit Python / templates** → restart the app to pick up changes:
  ```bash
  docker compose restart allianceauth_gunicorn allianceauth_worker allianceauth_worker_services allianceauth_beat
  ```
- **Add/rename models** → make and apply migrations:
  ```bash
  docker compose exec allianceauth_gunicorn python manage.py makemigrations wanderer
  docker compose exec allianceauth_gunicorn python manage.py migrate
  ```
- **Add a third-party dependency** → add it to
  [`conf/aa/requirements.txt`](conf/aa/requirements.txt) and rebuild:
  ```bash
  docker compose up -d --build
  ```
- **Register a new plugin app** in INSTALLED_APPS via
  [`conf/aa/local.py`](conf/aa/local.py).

## Layout

```
docker-compose.yml        Wanderer + Alliance Auth services (merged)
.env                      secrets + config (git-ignored)
wanderer-conf.env         Wanderer app config (git-ignored)
conf/aa/
  Dockerfile              builds the plugin-dev AA image
  local.py                AA settings override (DB, redis, ESI, plugins)
  celery.py               AA celery app
  nginx.conf              static files + reverse proxy for AA
  requirements.txt        extra pip packages for the AA image
plugins/wanderer/         the aa-wanderer plugin (editable install)
```

## Useful commands

```bash
docker compose ps                              # status
docker compose logs -f allianceauth_gunicorn   # AA web logs
docker compose exec allianceauth_gunicorn bash # shell in the AA container
docker compose down                            # stop (keeps volumes/data)
docker compose down -v                         # stop and DELETE all data
```
