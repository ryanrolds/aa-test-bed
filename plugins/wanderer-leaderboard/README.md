# aa-wanderer-leaderboard

Monthly mapping contribution leaderboard for a
[Wanderer](https://github.com/wanderer-industries/wanderer) map, as an
Alliance Auth app.

Wanderer already totals mapping contributions — but it totals them per
character, and it has no way of knowing that six characters are one person.
Alliance Auth does: it is the authoritative record of mains and alts. This app
reads Wanderer's audit API and rolls the numbers up per main, so a scanning
reward program pays out from one table instead of being reconciled by hand.

## Features

- Contributions credited to the person, not the character — alts roll up to
  their Alliance Auth main, with each character listed under the row
- Characters Alliance Auth does not know get their own row, marked unlinked
- Systems, connections and signatures, each split into created, updated and
  deleted, plus a total
- One month at a time, ranked, with the previous and next month a click away
- Track several maps and pick between them on the page

## For server admins

Nothing runs in the background and nothing is stored. Opening the page makes at
most one call to Wanderer for the selected map, and both that response and the
finished table are cached for five minutes
(`WANDERER_LEADERBOARD_CACHE_TTL`). Paging between months inside that window
costs no further calls, and the cache is shared, so a hundred people watching
the leaderboard cost the same as one. Editing a map's URL or API key discards
what the old ones fetched.

Wanderer only serves a rolling three month window, so older months cannot be
shown; the page says so rather than displaying a misleading zero.

## Installation

```bash
pip install -U aa-wanderer-leaderboard
```

Add `wanderer_leaderboard` to `INSTALLED_APPS`, then:

```bash
python manage.py migrate
```

Optional settings in `local.py`:

```python
WANDERER_LEADERBOARD_API_TIMEOUT = 30   # seconds
WANDERER_LEADERBOARD_CACHE_TTL = 300    # seconds a response is reused
```

Everything else is per map and lives in the admin. No database link to Wanderer
is required.

## Setup

1. Copy a map's **API key** from Wanderer's map settings.
2. In the Django admin, add a tracked map: its slug or map ID, the base URL of
   the Wanderer instance, and the API key. The **Test the API key against
   Wanderer** action confirms it works.
3. Grant users `wanderer_leaderboard | general | Can access the Wanderer
   Leaderboard`. The menu entry appears for them.

The base URL is called from the Alliance Auth server, not from your browser, so
it has to be reachable from there — behind Docker that is usually the Wanderer
service name rather than the localhost address you use in the browser.

Pick a map and a month on the page. One map is shown at a time.

## Tests

```bash
DJANGO_SETTINGS_MODULE=testauth.settings.local python runtests.py wanderer_leaderboard
```

Needs `allianceauth` and a reachable Redis; override with
`TESTAUTH_REDIS_URL=redis://aa_redis:6379/15`.

## Credits

Counts events produced by [Wanderer](https://github.com/wanderer-industries/wanderer).
Project layout follows allianceauth-workflows and Kalkoken's aa-example-app.
