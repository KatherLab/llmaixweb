# Account settings

The **Account settings** page (`/account`) manages your profile, password, and
connected sign-in methods.

## Profile

Edit your **Full Name** and **Email**. **Save profile** is enabled only when you
have unsaved changes.

## Change password

Enter your **current password**, then a **new password** and confirmation. The
update is enabled only when the current password is present, the new password
meets the minimum length, and the confirmation matches.

!!! note "Signing out other sessions"
    Changing your password signs you out of your other sessions. If you sign in
    exclusively via SSO you can leave this blank — but you may still set a
    password as a fallback.

## Connected accounts (SSO)

Shown only when single sign-on is enabled. Lists your linked identity providers
(name, account, last login) with a **Disconnect** button each.

!!! warning "You can't lock yourself out"
    You cannot disconnect your last remaining sign-in method — the app blocks it
    so you always keep a way in.

## Signing out

- **Sign out** — end the session on this device.
- **Sign out everywhere** — end all your sessions.
