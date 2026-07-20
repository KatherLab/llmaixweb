# User management

**User Management** (`/admin/user-management`) handles user accounts and
invitations.

## Inviting users

**+ Invite User** creates an invitation for an email address, with an optional
**Send invitation via email** toggle. If email delivery isn't configured, the app
shows the invitation link (`.../register?token=…`) with a **copy** button so you
can share it manually.

The **Invitations** list shows each invitation's email and whether it's been
used (hidden used ones by default). Invitations can be **deleted**.

## Managing users

The **Users** table shows each user's name, email, **status** (Active/Inactive),
and **role**. Click a user (or **Edit**) to open the editor:

- **General** — full name, email, **role** (User/Admin), and **status**
  (Active/Inactive).
- **Set Password** — set a new password for the user.
- **Danger Zone** — **Delete User**.

!!! warning "You can't change your own role or status"
    To prevent lockouts, an admin cannot change their own role or deactivate
    their own account from this screen.

!!! danger "Deleting a user cascades"
    Deleting a user permanently removes the account **and all data owned by that
    user** — their projects, files, documents, schemas, prompts, trials, and
    evaluations, plus their uploaded files in storage.

## Account lockout

There are two distinct mechanisms:

- **Manual** — setting a user **Inactive** blocks their login until reactivated.
- **Automatic** — after too many failed login attempts, an account is temporarily
  locked for a configured number of minutes and then unlocks itself. Successful
  login resets the counter.

There is no explicit "unlock" button — either wait out the automatic lockout, or
toggle the user's status.
