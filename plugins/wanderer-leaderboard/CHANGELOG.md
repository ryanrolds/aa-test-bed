# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [In Development] - Unreleased

### Added

- Monthly mapping contribution leaderboard for a Wanderer map, read live from
  `GET /api/map/audit` — no collection task, no snapshots, nothing to drift
- Nine metrics per contributor — systems, connections and signatures, each
  split into created, updated and deleted — plus a total
- Event types matched by category and action rather than exact name, so new
  Wanderer event variants are counted without a code change; ACL and admin
  events are ignored
- Batch events counted by their contents, so a signature batch or a multi
  system delete is worth what it actually covers
- Alt characters rolled up to their Alliance Auth main; characters Auth does
  not know show individually, marked unlinked
- One map and one month at a time, chosen on the page, with month paging and a
  clear notice for months older than the API's three month window
- Two layer caching: the raw audit window and the finished leaderboard rows,
  both keyed by the base URL and API key they were fetched with
- Per map API keys managed in the admin, with an action that tests a key
  against Wanderer. Failures show a short message on the page and the full
  request context in the log, never the key
- Menu entry and page gated behind the `basic_access` permission
