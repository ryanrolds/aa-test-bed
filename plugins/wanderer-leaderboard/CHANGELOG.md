# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [In Development] - Unreleased

### Changed

- Relicensed under AGPL-3
- Query logic moved out of `leaderboard.py` into model managers
- Packaging switched from setuptools to hatchling

### Added

- Test harness, tox config, pre-commit hooks and CI checks

## [0.3.0] - 2026-07-22

### Changed

- Read contributions from Wanderer's `user_activity_v1` event log instead of the
  `character-activity` API

### Added

- Rollup of alt contributions to each character's Alliance Auth main
