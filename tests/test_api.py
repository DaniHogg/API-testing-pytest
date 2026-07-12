"""Tests for the QA portfolio API (https://qa-portfolio-api.onrender.com).

Structure:
    - smoke: fast, core happy-path checks that must always pass.
    - regression: broader contract, error-path, edge-case, and CRUD coverage.

HTTP calls go through the session-scoped ``api_client`` fixture (see
conftest.py), which wraps requests.Session with the configured base_url and
timeout baked in. Response *shapes* are validated with jsonschema against the
schemas in tests/schemas.py rather than ad hoc ``field in dict`` checks.

A couple of tests intentionally assert behaviour that differs from what a
strict reading of the API's own /openapi.json would suggest (e.g. malformed
POST /posts payloads). Those were verified directly against the live
Render-hosted API and are documented inline -- see the module docstring
note near ``test_create_post_malformed_payload``.
"""

import jsonschema
import pytest

from schemas import ALBUM_SCHEMA, COMMENT_SCHEMA, POST_SCHEMA, TODO_SCHEMA, USER_SCHEMA, list_of


def _assert_json_response(response, expected_status: int) -> object:
    assert response.status_code == expected_status
    assert "application/json" in response.headers.get("content-type", "")
    return response.json()


# ---------------------------------------------------------------------------
# Smoke — basic availability and contract checks
# ---------------------------------------------------------------------------

@pytest.mark.smoke
def test_health_check(api_client):
    """API health endpoint returns 200 with status ok."""
    response = api_client.get("/health")
    body = _assert_json_response(response, 200)
    assert body["status"] == "ok"


@pytest.mark.smoke
def test_get_posts_returns_list(api_client):
    """GET /posts returns a non-empty list of posts matching the post schema."""
    response = api_client.get("/posts")
    posts = _assert_json_response(response, 200)
    assert isinstance(posts, list)
    assert len(posts) >= 1
    jsonschema.validate(instance=posts, schema=list_of(POST_SCHEMA))


@pytest.mark.smoke
def test_get_single_post(api_client):
    """GET /posts/1 returns the correct resource, matching the post schema."""
    response = api_client.get("/posts/1")
    post = _assert_json_response(response, 200)
    jsonschema.validate(instance=post, schema=POST_SCHEMA)
    assert post["id"] == 1


# ---------------------------------------------------------------------------
# Regression — broader contract, error path, and data-quality checks
# ---------------------------------------------------------------------------

@pytest.mark.regression
def test_content_type_header(api_client):
    """Responses carry an application/json Content-Type header."""
    response = api_client.get("/posts")
    assert "application/json" in response.headers.get("content-type", "")


@pytest.mark.regression
def test_get_users_returns_list(api_client):
    """GET /users returns a list of user objects matching the user schema
    (including nested address/geo/company)."""
    response = api_client.get("/users")
    users = _assert_json_response(response, 200)
    assert isinstance(users, list)
    assert len(users) >= 1
    jsonschema.validate(instance=users, schema=list_of(USER_SCHEMA))


@pytest.mark.regression
def test_filter_todos_by_completed(api_client):
    """GET /todos?completed=true returns only completed todos, matching the todo schema."""
    response = api_client.get("/todos", params={"completed": "true"})
    todos = _assert_json_response(response, 200)
    assert isinstance(todos, list)
    assert len(todos) >= 1
    jsonschema.validate(instance=todos, schema=list_of(TODO_SCHEMA))
    assert all(t["completed"] is True for t in todos)


@pytest.mark.regression
@pytest.mark.parametrize(
    "path",
    [
        pytest.param("/posts/99999", id="post"),
        pytest.param("/users/99999", id="user"),
    ],
)
def test_unknown_id_returns_404(api_client, path):
    """Requesting a post/user id that does not exist returns 404 with a detail message."""
    response = api_client.get(path)
    body = _assert_json_response(response, 404)
    assert isinstance(body.get("detail"), str)
    assert body["detail"].strip()


@pytest.mark.regression
@pytest.mark.parametrize(
    "path, params",
    [
        pytest.param("/posts", {"userId": 99999}, id="posts-by-unknown-user"),
        pytest.param("/albums", {"userId": 99999}, id="albums-by-unknown-user"),
    ],
)
def test_filter_by_unknown_user_returns_empty_list(api_client, path, params):
    """Edge: filtering by a non-existent userId should return an empty list, not an error."""
    response = api_client.get(path, params=params)
    items = _assert_json_response(response, 200)
    assert isinstance(items, list)
    assert items == []


# ---------------------------------------------------------------------------
# Malformed POST /posts payloads
#
# The audit asked for parametrized malformed-payload tests expecting 422,
# based on the assumption that request bodies are validated like the
# path/query parameters are. Verified live against the deployed API
# (https://qa-portfolio-api.onrender.com) this assumption does not hold: the
# service accepts a raw dict payload with no field-level validation, so:
#   - a missing "title"       -> 201, created with title == ""
#   - an empty JSON object    -> 201, created with title == "" and body == ""
#   - userId of the wrong type -> 500 Internal Server Error (the service
#     doesn't validate/coerce userId's type, and something downstream blows
#     up on it) -- this looks like a genuine bug in the API, not a design
#     choice, but it *is* the real, reproducible behaviour, so that's what
#     the test documents rather than an aspirational 422.
# Only a fully missing request body (no JSON at all) triggers FastAPI's own
# "body required" 422.
# ---------------------------------------------------------------------------

@pytest.mark.regression
@pytest.mark.parametrize(
    "label, payload, expected_status",
    [
        pytest.param("missing_title", {"body": "b", "userId": 1}, 201, id="missing-title"),
        pytest.param(
            "userId_wrong_type",
            {"title": "t", "body": "b", "userId": "not-an-int"},
            500,
            id="userId-wrong-type",
        ),
        pytest.param("empty_body", {}, 201, id="empty-object-body"),
    ],
)
def test_create_post_malformed_payload(api_client, label, payload, expected_status):
    """POST /posts with malformed payloads: documents actual (not assumed) behaviour."""
    response = api_client.post("/posts", json=payload)
    assert response.status_code == expected_status

    if expected_status == 201:
        created = response.json()
        assert "id" in created
        # Clean up so we don't leak resources onto the shared live backend.
        cleanup = api_client.delete(f"/posts/{created['id']}")
        assert cleanup.status_code == 200


@pytest.mark.regression
def test_create_post_missing_body_returns_422(api_client):
    """POST /posts with no JSON body at all is rejected by FastAPI's own body-required check."""
    response = api_client.post("/posts", headers={"Content-Type": "application/json"})
    body = _assert_json_response(response, 422)
    assert isinstance(body.get("detail"), list)


# ---------------------------------------------------------------------------
# Full post lifecycle: create -> update (PUT) -> update (PATCH) -> delete
#
# This single, self-contained test replaces the old test_create_post (which
# created a post and never cleaned it up, leaking a resource on every run of
# the shared live backend). It now exercises the previously-untested
# PUT/PATCH/DELETE verbs too, and guarantees cleanup via the DELETE call
# regardless of which assertions run.
# ---------------------------------------------------------------------------

@pytest.mark.regression
def test_post_lifecycle_create_update_delete(api_client):
    """POST creates a post; PUT replaces it; PATCH partially updates it; DELETE removes it."""
    create_payload = {"title": "test post", "body": "test body", "userId": 1}
    create_response = api_client.post("/posts", json=create_payload)
    created = _assert_json_response(create_response, 201)
    jsonschema.validate(instance=created, schema=POST_SCHEMA)
    assert created["title"] == create_payload["title"]
    assert created["userId"] == create_payload["userId"]
    post_id = created["id"]

    try:
        # --- PUT: full replace ---
        put_payload = {"title": "replaced title", "body": "replaced body", "userId": 2}
        put_response = api_client.put(f"/posts/{post_id}", json=put_payload)
        replaced = _assert_json_response(put_response, 200)
        jsonschema.validate(instance=replaced, schema=POST_SCHEMA)
        assert replaced["id"] == post_id
        assert replaced["title"] == put_payload["title"]
        assert replaced["body"] == put_payload["body"]
        assert replaced["userId"] == put_payload["userId"]

        # --- PATCH: partial update, only title changes ---
        patch_payload = {"title": "patched title"}
        patch_response = api_client.patch(f"/posts/{post_id}", json=patch_payload)
        patched = _assert_json_response(patch_response, 200)
        jsonschema.validate(instance=patched, schema=POST_SCHEMA)
        assert patched["id"] == post_id
        assert patched["title"] == patch_payload["title"]
        # Fields not included in the PATCH payload should be preserved.
        assert patched["body"] == put_payload["body"]
        assert patched["userId"] == put_payload["userId"]

        # GET should reflect the patched state.
        get_response = api_client.get(f"/posts/{post_id}")
        fetched = _assert_json_response(get_response, 200)
        assert fetched == patched
    finally:
        # --- DELETE, then confirm it's actually gone ---
        delete_response = api_client.delete(f"/posts/{post_id}")
        assert delete_response.status_code == 200

    get_after_delete = api_client.get(f"/posts/{post_id}")
    body = _assert_json_response(get_after_delete, 404)
    assert isinstance(body.get("detail"), str)


@pytest.mark.regression
@pytest.mark.parametrize(
    "verb, path_template",
    [
        pytest.param("put", "/posts/{id}", id="put"),
        pytest.param("patch", "/posts/{id}", id="patch"),
        pytest.param("delete", "/posts/{id}", id="delete"),
    ],
)
def test_update_or_delete_unknown_post_returns_404(api_client, verb, path_template):
    """PUT/PATCH/DELETE against a post id that doesn't exist all return 404."""
    path = path_template.format(id=99999)
    method = getattr(api_client, verb)
    kwargs = {} if verb == "delete" else {"json": {"title": "x", "body": "y", "userId": 1}}
    response = method(path, **kwargs)
    body = _assert_json_response(response, 404)
    assert isinstance(body.get("detail"), str)


# ---------------------------------------------------------------------------
# Comments (GET /posts/{id}/comments)
# ---------------------------------------------------------------------------

@pytest.mark.regression
def test_get_comments_for_post(api_client):
    """GET /posts/1/comments returns a list of comments, each tied to postId 1."""
    response = api_client.get("/posts/1/comments")
    comments = _assert_json_response(response, 200)
    assert isinstance(comments, list)
    assert len(comments) >= 1
    jsonschema.validate(instance=comments, schema=list_of(COMMENT_SCHEMA))
    assert all(c["postId"] == 1 for c in comments)


@pytest.mark.regression
def test_get_comments_for_nonexistent_post(api_client):
    """GET /{unknown}/comments returns 200 with an empty list rather than a 404.

    Verified live: the comments endpoint doesn't check that the parent post
    exists first, it just filters comments by postId -- an unknown postId
    simply matches nothing.
    """
    response = api_client.get("/posts/99999/comments")
    comments = _assert_json_response(response, 200)
    assert comments == []


# ---------------------------------------------------------------------------
# Albums (GET /albums, GET /albums?userId=)
# ---------------------------------------------------------------------------

@pytest.mark.regression
def test_get_albums_returns_list(api_client):
    """GET /albums returns a non-empty list of albums matching the album schema."""
    response = api_client.get("/albums")
    albums = _assert_json_response(response, 200)
    assert isinstance(albums, list)
    assert len(albums) >= 1
    jsonschema.validate(instance=albums, schema=list_of(ALBUM_SCHEMA))


@pytest.mark.regression
def test_get_albums_filtered_by_user(api_client):
    """GET /albums?userId=1 returns only albums owned by that user."""
    response = api_client.get("/albums", params={"userId": 1})
    albums = _assert_json_response(response, 200)
    assert isinstance(albums, list)
    assert len(albums) >= 1
    jsonschema.validate(instance=albums, schema=list_of(ALBUM_SCHEMA))
    assert all(a["userId"] == 1 for a in albums)


# ---------------------------------------------------------------------------
# Boundary / malformed path params
# ---------------------------------------------------------------------------

@pytest.mark.regression
@pytest.mark.parametrize(
    "post_id, expected_status",
    [
        pytest.param("0", 404, id="zero"),
        pytest.param("-1", 404, id="negative"),
        pytest.param("abc", 422, id="non-numeric"),
    ],
)
def test_get_post_boundary_path_params(api_client, post_id, expected_status):
    """GET /posts/{id} with boundary/malformed ids: 0 and -1 are well-formed
    integers that don't exist (404); a non-numeric id fails path validation (422)."""
    response = api_client.get(f"/posts/{post_id}")
    assert response.status_code == expected_status
    body = response.json()
    assert body.get("detail")
