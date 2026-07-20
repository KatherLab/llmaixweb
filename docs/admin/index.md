# Administration

Administrator-only areas for running LLMAIx Web. These are gated behind the admin
role and live under `/admin`.

| Page | What it covers |
| --- | --- |
| **[System settings](settings.md)** | System-wide configuration and secrets. |
| **[User management](user-management.md)** | Invitations, roles, activation, lockout. |
| **[Single sign-on (SSO)](sso.md)** | OIDC identity provider configuration. |
| **[Task monitoring](celery.md)** | Celery workers, queues, and task inspection. |

!!! tip "Activity bell"
    The bell in the app header shows live task activity (preprocessing and
    trials) for everyone. Admins additionally get a **View all activity** link to
    the [task monitoring](celery.md) page.
