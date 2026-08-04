"""Project sharing: who can reach a shared project, and how far.

Covers the three access levels (`owner` / `write` / `read`), the share
management endpoints, the read/write boundary on real project routes, and the
visibility rules (list endpoints, activity feeds, audit trail).
"""

import pytest

OWNER = ("test@example.com", "Testpassword1")
COLLAB = ("another@example.com", "Anotherpassword1")


@pytest.fixture
def owner_headers(login):
    return login(*OWNER)


@pytest.fixture
def collab_headers(login):
    return login(*COLLAB)


@pytest.fixture
def share(client, api_url):
    """Return `share(headers, project_id, email, permission) -> share dict`."""

    def _share(headers, project_id, email=COLLAB[0], permission="read"):
        resp = client.post(
            f"{api_url}/project/{project_id}/share",
            headers=headers,
            json={"email": email, "permission": permission},
        )
        assert resp.status_code == 200, resp.text
        return resp.json()

    return _share


# --------------------------------------------------------------------------- #
# Managing shares
# --------------------------------------------------------------------------- #
class TestShareManagement:
    def test_owner_can_share_and_list(
        self, client, api_url, owner_headers, make_project, share
    ):
        project = make_project(owner_headers, name="Shared Project")
        created = share(owner_headers, project["id"], permission="read")

        assert created["permission"] == "read"
        assert created["user"]["email"] == COLLAB[0]
        assert created["created_by"]["email"] == OWNER[0]

        resp = client.get(
            f"{api_url}/project/{project['id']}/share", headers=owner_headers
        )
        assert resp.status_code == 200, resp.text
        assert [s["user"]["email"] for s in resp.json()] == [COLLAB[0]]

    def test_sharing_twice_updates_instead_of_conflicting(
        self, client, api_url, owner_headers, make_project, share
    ):
        """Re-sharing is idempotent — it must not trip the unique constraint."""
        project = make_project(owner_headers, name="Re-share Project")
        first = share(owner_headers, project["id"], permission="read")
        second = share(owner_headers, project["id"], permission="write")

        assert second["id"] == first["id"]
        assert second["permission"] == "write"

        resp = client.get(
            f"{api_url}/project/{project['id']}/share", headers=owner_headers
        )
        assert len(resp.json()) == 1

    def test_share_with_unknown_email_is_404(
        self, client, api_url, owner_headers, make_project
    ):
        project = make_project(owner_headers, name="Unknown Share")
        resp = client.post(
            f"{api_url}/project/{project['id']}/share",
            headers=owner_headers,
            json={"email": "nobody@example.com", "permission": "read"},
        )
        assert resp.status_code == 404, resp.text

    def test_email_match_is_case_insensitive(
        self, client, api_url, owner_headers, make_project
    ):
        project = make_project(owner_headers, name="Case Share")
        resp = client.post(
            f"{api_url}/project/{project['id']}/share",
            headers=owner_headers,
            json={"email": COLLAB[0].upper(), "permission": "read"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["user"]["email"] == COLLAB[0]

    def test_cannot_share_with_the_owner(
        self, client, api_url, owner_headers, make_project
    ):
        project = make_project(owner_headers, name="Self Share")
        resp = client.post(
            f"{api_url}/project/{project['id']}/share",
            headers=owner_headers,
            json={"email": OWNER[0], "permission": "write"},
        )
        assert resp.status_code == 400, resp.text

    def test_owner_can_change_permission(
        self, client, api_url, owner_headers, make_project, share
    ):
        project = make_project(owner_headers, name="Repermission Project")
        created = share(owner_headers, project["id"], permission="read")

        resp = client.patch(
            f"{api_url}/project/{project['id']}/share/{created['id']}",
            headers=owner_headers,
            json={"permission": "write"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["permission"] == "write"

    def test_owner_can_revoke(
        self, client, api_url, owner_headers, collab_headers, make_project, share
    ):
        project = make_project(owner_headers, name="Revoke Project")
        created = share(owner_headers, project["id"], permission="write")

        resp = client.delete(
            f"{api_url}/project/{project['id']}/share/{created['id']}",
            headers=owner_headers,
        )
        assert resp.status_code == 200, resp.text

        # Access really is gone, not just the row.
        assert (
            client.get(
                f"{api_url}/project/{project['id']}", headers=collab_headers
            ).status_code
            == 403
        )

    def test_share_of_another_project_cannot_be_edited(
        self, client, api_url, owner_headers, make_project, share
    ):
        """Share ids are scoped by project, not just looked up by PK."""
        target = make_project(owner_headers, name="Target Project")
        other = make_project(owner_headers, name="Other Project")
        created = share(owner_headers, target["id"], permission="read")

        resp = client.patch(
            f"{api_url}/project/{other['id']}/share/{created['id']}",
            headers=owner_headers,
            json={"permission": "write"},
        )
        assert resp.status_code == 404, resp.text


# --------------------------------------------------------------------------- #
# Who may manage shares
# --------------------------------------------------------------------------- #
class TestShareManagementAuthorization:
    def test_write_collaborator_cannot_share_further(
        self, client, api_url, owner_headers, collab_headers, make_project, share
    ):
        """Full access stops short of widening the circle."""
        project = make_project(owner_headers, name="No Resharing")
        share(owner_headers, project["id"], permission="write")

        resp = client.post(
            f"{api_url}/project/{project['id']}/share",
            headers=collab_headers,
            json={"email": "admin@example.com", "permission": "write"},
        )
        assert resp.status_code == 403, resp.text

    def test_write_collaborator_cannot_delete_project(
        self, client, api_url, owner_headers, collab_headers, make_project, share
    ):
        project = make_project(owner_headers, name="No Deleting")
        share(owner_headers, project["id"], permission="write")

        resp = client.delete(
            f"{api_url}/project/{project['id']}", headers=collab_headers
        )
        assert resp.status_code == 403, resp.text
        # And the project is still there.
        assert (
            client.get(
                f"{api_url}/project/{project['id']}", headers=owner_headers
            ).status_code
            == 200
        )

    def test_collaborator_can_read_the_share_list(
        self, client, api_url, owner_headers, collab_headers, make_project, share
    ):
        project = make_project(owner_headers, name="Visible Roster")
        share(owner_headers, project["id"], permission="read")

        resp = client.get(
            f"{api_url}/project/{project['id']}/share", headers=collab_headers
        )
        assert resp.status_code == 200, resp.text
        assert len(resp.json()) == 1

    def test_collaborator_can_remove_their_own_share(
        self, client, api_url, owner_headers, collab_headers, make_project, share
    ):
        """ "Leave project" — the one mutation a non-owner may perform."""
        project = make_project(owner_headers, name="Leavable Project")
        created = share(owner_headers, project["id"], permission="read")

        resp = client.delete(
            f"{api_url}/project/{project['id']}/share/{created['id']}",
            headers=collab_headers,
        )
        assert resp.status_code == 200, resp.text
        assert (
            client.get(
                f"{api_url}/project/{project['id']}", headers=collab_headers
            ).status_code
            == 403
        )

    def test_stranger_cannot_see_the_share_list(
        self, client, api_url, owner_headers, collab_headers, make_project
    ):
        project = make_project(owner_headers, name="Private Roster")
        resp = client.get(
            f"{api_url}/project/{project['id']}/share", headers=collab_headers
        )
        assert resp.status_code == 403, resp.text


# --------------------------------------------------------------------------- #
# The read/write boundary on real project routes
# --------------------------------------------------------------------------- #
class TestReadOnlyCollaborator:
    def test_can_read_project_and_sub_resources(
        self,
        client,
        api_url,
        owner_headers,
        collab_headers,
        make_project,
        share,
        make_schema,
        make_prompt,
    ):
        project = make_project(owner_headers, name="Readable Project")
        make_schema(owner_headers, project["id"])
        make_prompt(owner_headers, project["id"])
        share(owner_headers, project["id"], permission="read")

        for path in (
            f"/project/{project['id']}",
            f"/project/{project['id']}/file",
            f"/project/{project['id']}/document",
            f"/project/{project['id']}/schema",
            f"/project/{project['id']}/prompt",
            f"/project/{project['id']}/trial",
            f"/project/{project['id']}/preprocess",
            f"/project/{project['id']}/groundtruth",
        ):
            resp = client.get(f"{api_url}{path}", headers=collab_headers)
            assert resp.status_code == 200, f"{path} → {resp.status_code} {resp.text}"

    def test_cannot_mutate(
        self, client, api_url, owner_headers, collab_headers, make_project, share
    ):
        project = make_project(owner_headers, name="Immutable Project")
        share(owner_headers, project["id"], permission="read")

        # Rename
        assert (
            client.put(
                f"{api_url}/project/{project['id']}",
                headers=collab_headers,
                json={"name": "Renamed by viewer"},
            ).status_code
            == 403
        )
        # Create a schema
        assert (
            client.post(
                f"{api_url}/project/{project['id']}/schema",
                headers=collab_headers,
                json={
                    "schema_name": "Sneaky",
                    "schema_definition": {"type": "object", "properties": {}},
                },
            ).status_code
            == 403
        )
        # Create a prompt
        assert (
            client.post(
                f"{api_url}/project/{project['id']}/prompt",
                headers=collab_headers,
                json={
                    "name": "Sneaky",
                    "system_prompt": "x",
                    "user_prompt": "y",
                    "project_id": project["id"],
                },
            ).status_code
            == 403
        )
        # Delete the project
        assert (
            client.delete(
                f"{api_url}/project/{project['id']}", headers=collab_headers
            ).status_code
            == 403
        )

    def test_read_only_denial_is_audited_as_insufficient_permission(
        self,
        client,
        api_url,
        owner_headers,
        collab_headers,
        admin_headers,
        make_project,
        share,
    ):
        project = make_project(owner_headers, name="Audited Boundary")
        share(owner_headers, project["id"], permission="read")

        client.put(
            f"{api_url}/project/{project['id']}",
            headers=collab_headers,
            json={"name": "nope"},
        )

        resp = client.get(
            f"{api_url}/admin/audit",
            headers=admin_headers,
            params={"action": "access_denied", "project_id": project["id"]},
        )
        rows = resp.json()["items"]
        assert rows, "expected a denial row"
        # Distinguishes a viewer hitting the boundary from a stranger probing.
        assert rows[0]["detail"]["reason"] == "insufficient_project_permission"
        assert rows[0]["detail"]["granted"] == "read"
        assert rows[0]["detail"]["permission"] == "write"


class TestWriteCollaborator:
    def test_can_rename_and_create_schemas(
        self, client, api_url, owner_headers, collab_headers, make_project, share
    ):
        project = make_project(owner_headers, name="Editable Project")
        share(owner_headers, project["id"], permission="write")

        resp = client.put(
            f"{api_url}/project/{project['id']}",
            headers=collab_headers,
            json={"name": "Renamed by editor"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["name"] == "Renamed by editor"
        # The response must not tell a collaborator they own the project.
        assert resp.json()["access_level"] == "write"

        resp = client.post(
            f"{api_url}/project/{project['id']}/schema",
            headers=collab_headers,
            json={
                "schema_name": "Editor Schema",
                "schema_definition": {"type": "object", "properties": {}},
            },
        )
        assert resp.status_code == 200, resp.text

    def test_cannot_transfer_ownership(
        self, client, api_url, owner_headers, collab_headers, make_project, share, login
    ):
        """`owner_id` stays admin-only, even for a write-level collaborator."""
        project = make_project(owner_headers, name="Ownership Guard")
        share(owner_headers, project["id"], permission="write")

        collab_id = client.get(f"{api_url}/user/me", headers=collab_headers).json()[
            "id"
        ]
        resp = client.put(
            f"{api_url}/project/{project['id']}",
            headers=collab_headers,
            json={"name": "Ownership Guard", "owner_id": collab_id},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["owner_id"] != collab_id


# --------------------------------------------------------------------------- #
# Visibility
# --------------------------------------------------------------------------- #
class TestVisibility:
    def test_shared_project_appears_in_the_collaborators_list(
        self, client, api_url, owner_headers, collab_headers, make_project, share
    ):
        project = make_project(owner_headers, name="Listed Project")

        before = client.get(f"{api_url}/project", headers=collab_headers).json()
        assert project["id"] not in [p["id"] for p in before]

        share(owner_headers, project["id"], permission="read")

        after = client.get(f"{api_url}/project", headers=collab_headers).json()
        listed = [p for p in after if p["id"] == project["id"]]
        assert listed, "shared project missing from the collaborator's list"
        assert listed[0]["access_level"] == "read"

    def test_access_level_and_share_count_on_detail(
        self, client, api_url, owner_headers, collab_headers, make_project, share
    ):
        project = make_project(owner_headers, name="Access Level Project")
        share(owner_headers, project["id"], permission="write")

        as_owner = client.get(
            f"{api_url}/project/{project['id']}", headers=owner_headers
        ).json()
        assert as_owner["access_level"] == "owner"
        assert as_owner["share_count"] == 1

        as_collab = client.get(
            f"{api_url}/project/{project['id']}", headers=collab_headers
        ).json()
        assert as_collab["access_level"] == "write"

    def test_new_project_reports_owner_access(
        self, client, api_url, owner_headers, make_project
    ):
        project = make_project(owner_headers, name="Fresh Project")
        assert project["access_level"] == "owner"
        assert project["share_count"] == 0

    def test_shares_are_removed_with_the_project(
        self, client, api_url, owner_headers, collab_headers, make_project, share
    ):
        project = make_project(owner_headers, name="Doomed Project")
        share(owner_headers, project["id"], permission="write")

        assert (
            client.delete(
                f"{api_url}/project/{project['id']}", headers=owner_headers
            ).status_code
            == 200
        )
        # The collaborator's project list must not carry a dangling entry.
        listed = client.get(f"{api_url}/project", headers=collab_headers).json()
        assert project["id"] not in [p["id"] for p in listed]
