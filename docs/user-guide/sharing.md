# Sharing projects

A project belongs to the user who created it. **Sharing** lets that owner give
other people access to the same project — either view-only or full editing —
without transferring ownership and without an administrator having to
intervene.

Shared projects appear in the collaborator's project list alongside their own,
marked with the access level they were given.

## Access levels

| | Viewer (`Can view`) | Editor (`Can edit`) | Owner |
| --- | :---: | :---: | :---: |
| Browse files, documents, schemas, prompts, runs, evaluations | ✓ | ✓ | ✓ |
| Download documents, results, and exports | ✓ | ✓ | ✓ |
| See who else the project is shared with | ✓ | ✓ | ✓ |
| Upload files and run preprocessing | | ✓ | ✓ |
| Create and edit schemas and prompts | | ✓ | ✓ |
| Start, cancel, and delete extraction runs | | ✓ | ✓ |
| Upload ground truth and create evaluations | | ✓ | ✓ |
| Rename the project / edit its description | | ✓ | ✓ |
| Add, change, or remove collaborators | | | ✓ |
| Delete the project | | | ✓ |
| Transfer ownership | | | administrators only |

!!! note "Why editors can't re-share"
    Sharing and deletion stay with the owner so that a project always has one
    accountable person who controls the circle of access. An editor can change
    the project's contents, but cannot widen who can reach the data in it.

## Sharing a project

1. Open the project and click the **gear icon** in the header to open
   **Project Settings**.
2. Scroll to the **Sharing** section.
3. Type the collaborator's **email address**, choose **Can view** or
   **Can edit**, and click **Add**.

The person must already have an account on this instance. If no active account
matches the address, the app reports that no active user was found — it does not
disclose whether the address is registered but deactivated. To bring in someone
who has no account yet, an administrator must first
[invite them](../admin/user-management.md).

!!! tip "Changing someone's access"
    Use the dropdown next to their name in the **Sharing** list to switch
    between **Can view** and **Can edit**. The change takes effect on their next
    request — they don't need to sign out.

## Removing access

Click the **✕** next to a collaborator to revoke their access. They lose the
project from their list immediately; nothing they created in the project is
deleted.

Collaborators can also remove *themselves* — that is the only sharing change a
non-owner may make. Deleting a project removes all of its shares along with it.

## What collaborators see

A viewer opening a shared project sees a **View-only access** banner at the top
of the workspace, and every control they can't use is hidden rather than shown
disabled: uploading and preprocessing, creating or editing schemas and prompts,
starting/renaming/cancelling/retrying/deleting extraction runs, uploading ground
truth, editing field mappings, and creating or deleting evaluations. Row
checkboxes for batch actions are hidden too, and the *Danger Zone* in project
settings is owner-only.

Everything that only reads stays available: browsing files and documents,
previewing and downloading, viewing results and evaluations, exporting metrics,
and viewing (but not editing) field mappings. The task-activity bell shows
progress for shared projects, but only offers **Cancel** on projects the user
can edit.

Live progress for preprocessing and extraction runs is delivered to every member
of a project, so a viewer watching a run started by someone else sees the same
real-time progress the owner does.

!!! warning "Sharing shares the data"
    A shared project exposes the full contents of that project — including
    uploaded source files and extracted document text, which may contain
    patient data — to the person you share with. Treat a share the same way you
    would treat handing over the files themselves, and check your organisation's
    rules on who may access which data before sharing. Every share, permission
    change, and revocation is written to the [audit log](../AUDIT_LOGGING.md).

## Administrators

Sharing is independent of the `ADMIN_ALL_PROJECT_ACCESS` setting. When that
setting is enabled, administrators can already reach every project and are
treated as owners; when it is disabled (the default), an administrator sees only
their own projects plus any that have been explicitly shared with them. See
[Security](../SECURITY.md) for the reasoning.
