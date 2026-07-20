# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project versions the **frontend** (`package.json`) and **backend**
(`pyproject.toml`) together under a single tag; where a change is specific to
one side it is noted inline.

For releases before `0.6.8`, see the
[GitHub Releases](https://github.com/KatherLab/llmaixweb/releases) and the git
history — this file was introduced at `0.6.8` and captures notable changes from
that point forward.

## [Unreleased]

### Added

- Project metadata: SPDX license, authors, keywords, classifiers, and project
  URLs in `pyproject.toml` and `package.json`.
- `SECURITY.md` vulnerability-disclosure policy (GitHub Security tab).
- `CITATION.cff` for academic citation.
- This `CHANGELOG.md`.
- Documentation site (MkDocs Material) with a per-page feature reference,
  including dedicated OCR-engines and troubleshooting pages.
- `THIRD_PARTY_NOTICES` generation and a license-compatibility check in CI.
- Frontend unit test suite (Vitest + Vue Test Utils) covering the shared
  `utils/` helpers and logic-heavy composables, run in CI.
- Playwright end-to-end smoke test driving the core workflow (login → project →
  upload → preprocess → trial → evaluation) against a broker-free backend and a
  fake LLM, run in CI.
- Localization (i18n) foundation (frontend): `vue-i18n` with lazy-loaded
  message catalogs for English, German, French, and Spanish, a navbar language
  switcher, and system-language auto-detection (persisted on explicit switch).
  Date/number formatting now follows the active locale. Catalog key-parity is
  enforced in CI via `npm run i18n:check`.
- Localized the full application UI (frontend): hardcoded strings across the
  auth, admin, projects, files, documents, schemas/prompts, trials, evaluation,
  ground-truth, landing, and shared-component views are now translated via
  `$t()` (~2,250 keys per locale in en/de/fr/es). A second CI guard,
  `npm run i18n:usage`, statically verifies every referenced message key exists
  in the source catalog. Backend error-message localization follows in a later
  phase.

### Changed

- Trimmed `README.md` to a landing page; the preprocessing/OCR guide, the
  environment-variable reference, and troubleshooting now live in the docs site
  (single source of truth).

### Fixed

- Projects list: search/table spacing and gating of the "all projects" toggle
  behind the admin project-access flag.
- CSV/XLSX import: no longer pre-selects a text column on the first import
  configuration.

## [0.6.8] — 2026-07-20

### Added

- Ground-truth mapping modal: schema field pre-selection and improved error
  handling; merge auto-mapping; export pre-selection.
- Evaluation: comparison-method chips, tiered accuracy bars, re-evaluate
  confirmation.
- Documents: select-all, sorting, configurable page size; full-group CSV export.

### Changed

- Files/documents flow: smoother preprocessing-complete hand-off; masked API
  keys in the UI.

### Fixed

- Safer project deletion and upload cancellation.

## [0.6.7] and earlier

See the [GitHub Releases page](https://github.com/KatherLab/llmaixweb/releases)
and the git commit history for details.

[Unreleased]: https://github.com/KatherLab/llmaixweb/compare/v0.6.8...HEAD
[0.6.8]: https://github.com/KatherLab/llmaixweb/compare/v0.6.7...v0.6.8
