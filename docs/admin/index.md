# Administration

Administrator-only areas for running LLMAIx Web. These are gated behind the admin
role and live under `/admin`. The whole section is reachable from the gear
**Admin** link in the app header, which only appears for users whose role is
**Admin**. Non-admins who navigate to any `/admin/*` URL are redirected away.

The admin area is a single tabbed dashboard: switching between the pages below
keeps you inside the same shell. Opening `/admin` with no sub-page redirects to
**User management**, which is the default landing view.

<figure markdown>
  ![Admin User Management landing page with users table and invitations panel](../assets/screenshots/admin-user-management.png){ width="820" }
  <figcaption>Opening /admin lands on User Management: the users table plus the invitations panel.</figcaption>
</figure>

| Page | Route | What it covers |
| --- | --- | --- |
| **[User management](user-management.md)** | `/admin/user-management` | Invitations, roles, activation, lockout. The default `/admin` view. |
| **[System settings](settings.md)** | `/admin/settings` | System-wide configuration and secrets, grouped into category tabs. |
| **[Single sign-on (SSO)](sso.md)** | `/admin/sso` | OIDC identity provider configuration. |
| **[Audit log](../AUDIT_LOGGING.md)** | `/admin/audit` | Append-only activity trail and the central error log. |
| **[Task monitoring](celery.md)** | `/admin/celery` | Celery workers, queues, and task inspection. |

!!! note "Which tabs appear"
    Some tabs are gated by deployment configuration. For example, the SSO tab is
    only useful once SSO is enabled in settings, and task monitoring assumes
    Celery is running. Tabs that don't apply to your deployment may be hidden or
    show an empty/reminder state rather than being removed entirely.

!!! tip "Activity bell"
    The bell in the app header shows live task activity (preprocessing and
    trials) for everyone. Admins additionally get a **View all activity** link to
    the [task monitoring](celery.md) page.
