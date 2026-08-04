# aa-wanderer-leaderboard

Who actually mapped anything this month? Now you can find out.

## What does it do?

Builds a monthly contribution leaderboard for a
[Wanderer](https://github.com/wanderer-industries/wanderer) map, so you can pay your
best mappers what they are owed. Wanderer records all the activity but never totals
it up, so this reads its audit API and does the counting.

Contributions get broken out nine ways: systems, connections and signatures, each
split into created, updated and deleted.

| Column | Wanderer event_name | Counted as |
|---|---|---|
| Systems created / updated / deleted | `system_added` / `system_updated` / `systems_removed` | events, deletes count `solar_system_ids[]` |
| Connections created / updated / deleted | `map_connection_added` / `..._updated` / `..._removed` | events |
| Signatures created / updated / deleted | `signatures_added` / `..._updated` / `..._removed` | length of `signatures[]` |
| Total | all nine added up | |

Event types are matched by category and action instead of by exact name, so new
variants get picked up on their own. ACL and admin events are ignored. Where one
event covers several items, a batch of signatures or a multi system delete, the count
comes from the array length in `event_data`.

Alts are rolled up to their Alliance Auth main, so each person gets one row and one
payout, with their contributing characters listed underneath. Characters that are not
registered in Auth cannot be linked, so those get their own row marked unlinked.

Everything is worked out on page load straight from the audit API. No collection
task, no snapshots, and no stored copy to drift out of date. Calendar months come
from each event's `inserted_at`.

### Why the audit endpoint and not character-activity

Wanderer's `character-activity` endpoint only gives you coarse connections,
signatures and passages totals. It leaves out systems completely and does not split
created from updated from deleted. `GET /api/map/audit` hands back the raw events
instead — `event_name`, `event_data` and the acting character — which is everything
the nine columns need.

The catch is that audit only accepts a relative period, `1H` through `3M`, with no
way to ask for a specific month. So the plugin pulls `3M` and slices the selected
month out itself. Months further back than that are gone as far as the API is
concerned, and the page says so rather than showing a misleading zero.

## Todo

- Per corp and per alliance filtering
- Configurable weighting per metric for payout math
- Persist pulled events so history outlives the API's three month window

## Installation

`pip install -U aa-wanderer-leaderboard`

Add `'wanderer_leaderboard'` to `INSTALLED_APPS`, then `python manage.py migrate`.

Optionally, in `local.py`:

```python
# fallback for tracked maps that don't set their own base URL
WANDERER_LEADERBOARD_BASE_URL = "https://wanderer.example.com"
WANDERER_LEADERBOARD_API_TIMEOUT = 30   # seconds
WANDERER_LEADERBOARD_CACHE_TTL = 300    # seconds an audit response is reused
```

No database link to Wanderer is required.

## Usage

Copy a map's **API key** out of Wanderer, then in the admin panel add a tracked map
with its slug or map id and paste the key in. The **Test the API key against
Wanderer** admin action tells you straight away whether it works. Then grant users
`wanderer_leaderboard | general | Can access the Wanderer Leaderboard` and the
Wanderer Leaderboard menu entry shows up for them.

Pick a map and a month on the page itself. Data is live, so there is nothing to
collect first.

## Tests

```bash
DJANGO_SETTINGS_MODULE=testauth.settings.local python runtests.py wanderer_leaderboard
```

Needs `allianceauth` and a reachable Redis; point elsewhere with
`TESTAUTH_REDIS_URL=redis://aa_redis:6379/15` to run inside the compose stack.

## Credits

Counts events produced by [Wanderer](https://github.com/wanderer-industries/wanderer).
Project layout follows allianceauth-workflows and Kalkoken's aa-example-app.
