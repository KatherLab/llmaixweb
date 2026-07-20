# System settings

**App Settings** (`/admin/settings`) configures the running system. Settings are
grouped into category tabs — General, Security, SSO, OpenAI, OCR, docling-serve,
Preprocessing, Storage, Database, Email.

## How settings work

Each setting is edited according to its type:

- **Read-only (.env)** — set only via the environment; shown with a lock icon and
  its `KEY=value` example. These can't be changed from the UI.
- **Secret** — shown as **Set** / **Not Set**, never revealing the value. **Set/
  Update** reveals a password field; **Clear** removes the override. Secrets are
  stored **encrypted** at rest.
- **Boolean / integer / string** — a checkbox, number, or text field.

A **Revert** button appears on any setting you've overridden, returning it to the
environment default.

!!! note "Only differences are stored"
    A runtime override is saved only when it **differs** from the environment
    default; setting a value back to the default removes the override. Setting
    changes are audited (keys only — never the values).

For the full catalog of settings and what each does, see
[`.env.example`](https://github.com/KatherLab/llmaixweb/blob/main/.env.example)
and the [Configuration](../operations/configuration.md) page.

!!! tip "OCR engines"
    The OCR-related tabs are where you enable the engines that appear in the
    [preprocessing](../user-guide/preprocessing.md) panel (local Docling/Tesseract,
    Mistral OCR, Vision LLM) and set their default endpoints and models.
