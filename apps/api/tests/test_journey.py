"""The end-to-end journey from PRODUCT.md.

One test that walks the whole thing: sign up, build an app, test it, publish
it, invite two colleagues, have one submit a request and the other approve it,
and check the outcome landed. If this passes, the product works.

The rest of the file is the permission checks that make the journey safe —
those matter as much as the happy path, because the happy path is what gets
demoed and the permission checks are what get exploited.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.db import get_session
from app.main import app


@pytest.fixture
def client(engine):
    """A client wired to the test database instead of the real one."""
    maker = sessionmaker(bind=engine, expire_on_commit=False)

    def override():
        session = maker()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def owner_token(client) -> str:
    response = client.post(
        "/api/auth/signup",
        json={"email": "asha@shop.com", "name": "Asha", "password": "correct-horse"},
    )
    assert response.status_code == 201, response.text
    return response.json()["token"]


# --------------------------------------------------------------------------
# The journey
# --------------------------------------------------------------------------


def test_the_whole_thing(client, owner_token):
    owner = auth(owner_token)

    # 1. The owner starts from a template.
    created = client.post(
        "/api/projects/from-template",
        json={"template": "leave_management"},
        headers=owner,
    )
    assert created.status_code == 201, created.text
    project = created.json()
    project_id = project["id"]
    assert project["status"] == "draft"
    assert project["public_path"].startswith("/a/")

    # 2. They read the plan in plain English before trusting it.
    detail = client.get(f"/api/projects/{project_id}", headers=owner).json()
    plan = detail["plan"]
    assert plan["counts"] == {
        "roles": 3,
        "entities": 1,
        "screens": 4,
        "workflows": 1,
        "steps": 5,
    }
    manager = next(p for p in plan["people"] if p["name"] == "manager")
    assert manager["can_approve"] is True
    sentences = [s["sentence"] for s in plan["workflows"][0]["steps"]]
    assert "Wait for the manager to approve or reject it" in sentences

    # 3. They press Test and watch it run, without creating any real data.
    tested = client.post(
        f"/api/projects/{project_id}/test-run",
        json={
            "workflow_key": "leave_approval",
            "data": {"leave_type": "Casual", "start_date": "2026-04-01", "days": 3},
            "approve": True,
        },
        headers=owner,
    )
    assert tested.status_code == 200, tested.text
    run = tested.json()["run"]
    assert run["status"] == "completed"
    assert [s["step_id"] for s in run["steps"]] == [
        "notify_manager",
        "manager_decision",
        "mark_approved",
        "notify_employee",
    ]
    assert all(s["status"] == "ok" for s in run["steps"])
    # The test left nothing behind.
    assert client.get(f"/api/projects/{project_id}/runs", headers=owner).json()["runs"] == []

    # 4. They publish it.
    published = client.post(f"/api/projects/{project_id}/publish", headers=owner)
    assert published.status_code == 200, published.text
    slug = published.json()["slug"]
    assert published.json()["is_published"] is True

    # 5. They invite two colleagues.
    invites = {}
    for role, name, email in [
        ("employee", "Ravi", "ravi@shop.com"),
        ("manager", "Meera", "meera@shop.com"),
    ]:
        response = client.post(
            f"/api/projects/{project_id}/members",
            json={"email": email, "name": name, "role": role},
            headers=owner,
        )
        assert response.status_code == 201, response.text
        invites[role] = response.json()["invite_token"]

    # 6. Both set a password from their invite link.
    tokens = {}
    for role, invite_token in invites.items():
        response = client.post(
            f"/api/a/{slug}/join",
            json={"token": invite_token, "password": "my-good-password"},
        )
        assert response.status_code == 200, response.text
        tokens[role] = response.json()["token"]

    employee, boss = auth(tokens["employee"]), auth(tokens["manager"])

    # 7. The employee sees only their own pages.
    me = client.get(f"/api/a/{slug}/me", headers=employee).json()
    assert me["user"]["role_label"] == "Employee"
    assert [n["key"] for n in me["nav"]] == ["request_leave", "my_requests"]

    # 8. The employee requests leave.
    submitted = client.post(
        f"/api/a/{slug}/screens/request_leave/submit",
        json={
            "data": {
                "leave_type": "Casual",
                "start_date": "2026-04-10",
                "days": 2,
                "reason": "Family function",
            }
        },
        headers=employee,
    )
    assert submitted.status_code == 201, submitted.text
    record_id = submitted.json()["record_id"]
    assert submitted.json()["workflow"]["status"] == "waiting_approval"

    # 9. The manager finds it waiting for them.
    queue = client.get(f"/api/a/{slug}/screens/pending_approvals", headers=boss)
    assert queue.status_code == 200, queue.text
    items = queue.json()["approvals"]
    assert len(items) == 1
    assert items[0]["record"]["values"]["reason"] == "Family function"
    assert items[0]["record"]["submitted_by"] == "Ravi"
    assert items[0]["prompt"] == "Approve this leave request?"

    # 10. The manager approves it.
    decided = client.post(
        f"/api/a/{slug}/approvals/{items[0]['approval_id']}",
        json={"approved": True, "note": "Enjoy"},
        headers=boss,
    )
    assert decided.status_code == 200, decided.text
    assert decided.json()["run"]["status"] == "completed"

    # 11. The record shows the outcome, and the queue is empty again.
    record = client.get(
        f"/api/a/{slug}/records/leave_requests/{record_id}", headers=boss
    ).json()
    assert record["record"]["values"]["status"] == "Approved"
    assert client.get(
        f"/api/a/{slug}/screens/pending_approvals", headers=boss
    ).json()["approvals"] == []

    # 12. The employee was told.
    notifications = client.get(f"/api/a/{slug}/notifications", headers=employee).json()
    assert notifications["unread"] == 1
    assert notifications["notifications"][0]["title"] == "Your leave request was decided"

    # 13. The owner can see the real run in their history.
    runs = client.get(f"/api/projects/{project_id}/runs", headers=owner).json()["runs"]
    assert len(runs) == 1
    assert runs[0]["status"] == "completed"
    assert runs[0]["sequence"] == 1


# --------------------------------------------------------------------------
# Permissions — the part that has to hold
# --------------------------------------------------------------------------


@pytest.fixture
def live_app(client, owner_token):
    """A published leave app with an employee and a manager signed up."""
    owner = auth(owner_token)
    project = client.post(
        "/api/projects/from-template",
        json={"template": "leave_management"},
        headers=owner,
    ).json()
    slug = client.post(
        f"/api/projects/{project['id']}/publish", headers=owner
    ).json()["slug"]

    tokens = {}
    for role, name, email in [
        ("employee", "Ravi", "ravi@shop.com"),
        ("manager", "Meera", "meera@shop.com"),
        ("employee", "Sunil", "sunil@shop.com"),
    ]:
        invite = client.post(
            f"/api/projects/{project['id']}/members",
            json={"email": email, "name": name, "role": role},
            headers=owner,
        ).json()
        tokens[name] = client.post(
            f"/api/a/{slug}/join",
            json={"token": invite["invite_token"], "password": "another-password"},
        ).json()["token"]

    return {"project": project, "slug": slug, "tokens": tokens, "owner": owner}


def test_an_employee_cannot_open_the_approvals_screen(client, live_app):
    response = client.get(
        f"/api/a/{live_app['slug']}/screens/pending_approvals",
        headers=auth(live_app["tokens"]["Ravi"]),
    )
    assert response.status_code == 403
    assert "access" in response.json()["detail"].lower()


def test_an_employee_cannot_read_a_colleagues_request(client, live_app):
    slug = live_app["slug"]
    ravi = auth(live_app["tokens"]["Ravi"])
    sunil = auth(live_app["tokens"]["Sunil"])

    record_id = client.post(
        f"/api/a/{slug}/screens/request_leave/submit",
        json={"data": {"leave_type": "Sick", "start_date": "2026-05-01", "days": 1}},
        headers=ravi,
    ).json()["record_id"]

    # Sunil's own list is empty...
    assert client.get(f"/api/a/{slug}/screens/my_requests", headers=sunil).json()["total"] == 0
    # ...and he cannot reach Ravi's record by guessing its id.
    denied = client.get(f"/api/a/{slug}/records/leave_requests/{record_id}", headers=sunil)
    assert denied.status_code == 403


def test_an_employee_cannot_decide_an_approval(client, live_app):
    slug = live_app["slug"]
    ravi = auth(live_app["tokens"]["Ravi"])

    client.post(
        f"/api/a/{slug}/screens/request_leave/submit",
        json={"data": {"leave_type": "Casual", "start_date": "2026-05-01", "days": 1}},
        headers=ravi,
    )
    approval_id = client.get(
        f"/api/a/{slug}/screens/pending_approvals", headers=auth(live_app["tokens"]["Meera"])
    ).json()["approvals"][0]["approval_id"]

    denied = client.post(
        f"/api/a/{slug}/approvals/{approval_id}", json={"approved": True}, headers=ravi
    )
    assert denied.status_code == 403


def test_a_form_cannot_be_used_to_set_a_field_it_does_not_offer(client, live_app):
    """The form's field list is the allowlist, not a suggestion."""
    slug = live_app["slug"]
    submitted = client.post(
        f"/api/a/{slug}/screens/request_leave/submit",
        json={
            "data": {
                "leave_type": "Casual",
                "start_date": "2026-05-01",
                "days": 1,
                # Not on the form. A workflow decides this.
                "status": "Approved",
                "decision_note": "I approved myself",
            }
        },
        headers=auth(live_app["tokens"]["Ravi"]),
    )
    assert submitted.status_code == 201

    record = client.get(
        f"/api/a/{slug}/records/leave_requests/{submitted.json()['record_id']}",
        headers=auth(live_app["tokens"]["Meera"]),
    ).json()["record"]["values"]

    assert record["status"] == "Pending"
    assert record["decision_note"] is None


def test_an_app_token_does_not_work_on_another_app(client, live_app, owner_token):
    """A token minted for one published app must not open another."""
    owner = auth(owner_token)
    other = client.post(
        "/api/projects/from-template",
        json={"template": "expense_approval"},
        headers=owner,
    ).json()
    other_slug = client.post(
        f"/api/projects/{other['id']}/publish", headers=owner
    ).json()["slug"]

    response = client.get(
        f"/api/a/{other_slug}/me", headers=auth(live_app["tokens"]["Meera"])
    )
    assert response.status_code == 401


def test_an_app_token_does_not_work_on_the_dashboard(client, live_app):
    response = client.get("/api/projects", headers=auth(live_app["tokens"]["Meera"]))
    assert response.status_code == 401


def test_a_platform_token_does_not_work_inside_an_app(client, live_app, owner_token):
    response = client.get(f"/api/a/{live_app['slug']}/me", headers=auth(owner_token))
    assert response.status_code == 401


def test_one_owner_cannot_see_anothers_project(client, owner_token, live_app):
    stranger = client.post(
        "/api/auth/signup",
        json={"email": "other@x.com", "name": "Other", "password": "different-pass"},
    ).json()["token"]

    response = client.get(
        f"/api/projects/{live_app['project']['id']}", headers=auth(stranger)
    )
    assert response.status_code == 404  # not 403 — we do not confirm it exists


def test_an_unpublished_app_is_not_reachable(client, owner_token):
    owner = auth(owner_token)
    project = client.post(
        "/api/projects/from-template",
        json={"template": "leave_management"},
        headers=owner,
    ).json()

    assert client.get(f"/api/a/{project['slug']}/info").status_code == 404

    client.post(f"/api/projects/{project['id']}/publish", headers=owner)
    assert client.get(f"/api/a/{project['slug']}/info").status_code == 200

    client.post(f"/api/projects/{project['id']}/unpublish", headers=owner)
    assert client.get(f"/api/a/{project['slug']}/info").status_code == 404


def test_editing_a_draft_does_not_change_the_live_app(client, owner_token):
    """Publish is the only thing that changes what users see."""
    owner = auth(owner_token)
    project = client.post(
        "/api/projects/from-template",
        json={"template": "leave_management"},
        headers=owner,
    ).json()
    project_id = project["id"]
    slug = client.post(f"/api/projects/{project_id}/publish", headers=owner).json()["slug"]

    spec = client.get(f"/api/projects/{project_id}", headers=owner).json()["spec"]
    spec["name"] = "Renamed While Live"
    updated = client.patch(
        f"/api/projects/{project_id}", json={"spec": spec}, headers=owner
    )
    assert updated.status_code == 200
    assert updated.json()["has_unpublished_changes"] is True

    # The live app still shows the published name.
    assert client.get(f"/api/a/{slug}/info").json()["name"] == "Employee Leave Management"

    client.post(f"/api/projects/{project_id}/publish", headers=owner)
    assert client.get(f"/api/a/{slug}/info").json()["name"] == "Renamed While Live"


# --------------------------------------------------------------------------
# Input handling
# --------------------------------------------------------------------------


def test_a_missing_required_field_is_reported_per_field(client, live_app):
    response = client.post(
        f"/api/a/{live_app['slug']}/screens/request_leave/submit",
        json={"data": {"leave_type": "Casual"}},
        headers=auth(live_app["tokens"]["Ravi"]),
    )
    assert response.status_code == 422
    errors = response.json()["detail"]["field_errors"]
    assert "start_date" in errors
    assert "days" in errors
    assert errors["days"] == "Number of days is required"


def test_a_choice_outside_the_list_is_refused(client, live_app):
    response = client.post(
        f"/api/a/{live_app['slug']}/screens/request_leave/submit",
        json={
            "data": {"leave_type": "Sabbatical", "start_date": "2026-05-01", "days": 1}
        },
        headers=auth(live_app["tokens"]["Ravi"]),
    )
    assert response.status_code == 422
    assert "Casual" in response.json()["detail"]["field_errors"]["leave_type"]


def test_an_invalid_spec_is_refused_with_reasons(client, owner_token):
    owner = auth(owner_token)
    project = client.post(
        "/api/projects/from-template",
        json={"template": "leave_management"},
        headers=owner,
    ).json()

    spec = client.get(f"/api/projects/{project['id']}", headers=owner).json()["spec"]
    # Point a screen at an entity that does not exist.
    spec["screens"][0]["entity"] = "imaginary_things"

    response = client.patch(
        f"/api/projects/{project['id']}", json={"spec": spec}, headers=owner
    )
    assert response.status_code == 422
    messages = [e["message"] for e in response.json()["detail"]["errors"]]
    assert any("imaginary_things" in m for m in messages)


def test_a_reserved_slug_is_refused(client, owner_token):
    owner = auth(owner_token)
    project = client.post(
        "/api/projects/from-template",
        json={"template": "leave_management"},
        headers=owner,
    ).json()

    response = client.patch(
        f"/api/projects/{project['id']}", json={"slug": "login"}, headers=owner
    )
    assert response.status_code == 400
    assert "reserved" in response.json()["detail"]


def test_signing_up_twice_with_one_email_is_refused(client, owner_token):
    response = client.post(
        "/api/auth/signup",
        json={"email": "ASHA@shop.com", "name": "Asha again", "password": "another-one"},
    )
    assert response.status_code == 409


def test_a_short_password_is_refused(client):
    response = client.post(
        "/api/auth/signup",
        json={"email": "new@x.com", "name": "New", "password": "short"},
    )
    assert response.status_code == 400
    assert "8 characters" in response.json()["detail"]


def test_wrong_credentials_do_not_reveal_whether_the_email_exists(client, owner_token):
    known = client.post(
        "/api/auth/login", json={"email": "asha@shop.com", "password": "wrong-password"}
    )
    unknown = client.post(
        "/api/auth/login", json={"email": "nobody@x.com", "password": "wrong-password"}
    )
    assert known.status_code == unknown.status_code == 401
    assert known.json()["detail"] == unknown.json()["detail"]


def test_health_reports_which_provider_is_live(client):
    body = client.get("/api/health").json()
    assert body["ok"] is True
    assert body["ai_provider"] in ("groq", "anthropic", "echo")
