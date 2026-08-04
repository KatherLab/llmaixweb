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

- Audit log now records denied access: an authenticated user refused a project
  they don't own, or a non-admin hitting an admin route, is written as
  `access_denied` (outcome `denied`) with the attempted method and path.
  Filterable under a new "Authorization" group in the audit viewer. Repeated
  identical denials collapse to one row per minute so a client hammering a
  forbidden endpoint can't inflate the trail.
- Audit log now records SSO identity changes: linking a sign-in method to an
  existing account, SSO just-in-time account provisioning, and a user unlinking
  their own identity.

### Changed

- Renamed "Trials" to "Extraction Runs" in the UI (API and database keep the term "trial").

## [0.8.0] — 2026-08-03

### Added

- Trial results viewer: click an extracted value to highlight where it came from
  in the source text. Matches are found by text search and graded by confidence.
- Optional *Ask for source quotes* (below the model in the trial dialog): the
  model cites the passage behind each value, making the highlights exact, and
  adds a few words on values it could not quote ("explicitly denied", "not
  mentioned"). Doubles output tokens; off by default.
- Start New Trial: model pre-filled from the project's last run, missing required
  inputs outlined in amber, compact document and group lists, and less
  explanatory text.
- Prompts follow the interface language: the starter template comes in English,
  German, French and Spanish, and the instructions the app appends to every
  request (safety notice, schema line, source-quote rules) are localized too.
  Both are overridable — per prompt in the editor, per trial under Advanced
  Settings.
- Schemas are validated on save and at trial creation — a stale `required` entry
  used to fail every document in a run.

### Fixed

- Browsers no longer autofill a saved password into the trial's custom API key
  field, which silently switched the trial to a custom endpoint and broke the
  model list.
- Token-capped responses are retried with a larger budget whenever unusable, not
  only when they came back empty.
- Results cut off at the token cap are reported as `incomplete`, and
  provider-filtered ones as `refused`.
- JSON result viewer: objects nested inside arrays can be expanded again.

## [0.7.2] — 2026-07-29

### Security

- SSRF hardening: validation of user-supplied LLM/OCR `base_url`s now also
  blocks cloud instance-metadata addresses written in alternate numeric IP
  notations (decimal/hex/octal), not just dotted-quad.

### Fixed

- Admin Celery monitoring endpoints now return a clear 503 ("monitoring
  unavailable") instead of a 500 when Celery is disabled (`DISABLE_CELERY`).
- Evaluation matching is more robust: blank/missing ground-truth IDs no longer
  collide under a literal `"None"`/`"nan"` key, and automatic field-mapping
  suggestions now fire for underscore/suffix column-name variants.
- Schema type validation no longer accepts a boolean where an integer/number is
  expected.
- LLM extraction: JSON responses delimited with typographic ("curly") quotes are
  now repaired correctly instead of being rejected as invalid JSON — the
  smart-quote normalization step had been silently disabled.
- LLM extraction: a prompt consisting of only a system prompt (with no
  `{document_content}` placeholder and no user prompt) now still sends the
  document to the model, instead of running the extraction against no content.

## [0.7.1] — 2026-07-21

### Added

- Trial results download can now optionally include the model's reasoning and
  token usage per document.

### Fixed

- Tables/headers no longer clip row actions when labels are long (e.g. in
  German, French, and Spanish).

## [0.7.0] — 2026-07-20

### Added

- Localization (i18n): the full UI is now available in English, German,
  French, and Spanish, with a language switcher and automatic system-language
  detection. Backend error messages are localized too.
- Documentation site: https://katherlab.github.io/llmaixweb/, with setup,
  usage, and troubleshooting guides.
- `SECURITY.md` vulnerability-disclosure policy and `CITATION.cff` for
  academic citation.

### Changed

- `README.md` trimmed to a landing page; detailed setup/usage guides moved to
  the documentation site.

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

[Unreleased]: https://github.com/KatherLab/llmaixweb/compare/v0.8.0...HEAD
[0.8.0]: https://github.com/KatherLab/llmaixweb/compare/v0.7.2...v0.8.0
[0.7.2]: https://github.com/KatherLab/llmaixweb/compare/v0.7.1...v0.7.2
[0.7.1]: https://github.com/KatherLab/llmaixweb/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/KatherLab/llmaixweb/compare/v0.6.8...v0.7.0
[0.6.8]: https://github.com/KatherLab/llmaixweb/compare/v0.6.7...v0.6.8
