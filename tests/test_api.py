import pytest
import requests


REQUEST_TIMEOUT_SECONDS = 15


def _get(base_url: str, path: str, **kwargs) -> requests.Response:
    return requests.get(f"{base_url}{path}", timeout=REQUEST_TIMEOUT_SECONDS, **kwargs)


def _post(base_url: str, path: str, **kwargs) -> requests.Response:
    return requests.post(f"{base_url}{path}", timeout=REQUEST_TIMEOUT_SECONDS, **kwargs)


def _assert_json_response(response: requests.Response, expected_status: int) -> dict:
    assert response.status_code == expected_status
    assert "application/json" in response.headers.get("content-type", "")
    return response.json()


# ---------------------------------------------------------------------------
# Smoke — basic availability and contract checks
# ---------------------------------------------------------------------------

@pytest.mark.smoke
def test_health_check(base_url):
    """API health endpoint returns 200 with status ok."""
    response = _get(base_url, "/health")
    body = _assert_json_response(response, 200)
    assert body["status"] == "ok"


@pytest.mark.smoke
def test_get_posts_returns_list(base_url):
    """GET /posts returns a non-empty list of posts with the expected fields."""
    response = _get(base_url, "/posts")
    posts = _assert_json_response(response, 200)
    assert isinstance(posts, list)
    assert len(posts) >= 1
    for field in ("id", "userId", "title", "body"):
        assert field in posts[0]


@pytest.mark.smoke
def test_get_single_post(base_url):
    """GET /posts/1 returns the correct resource."""
    response = _get(base_url, "/posts/1")
    post = _assert_json_response(response, 200)
    assert post["id"] == 1
    assert isinstance(post["userId"], int)
    assert "title" in post


# ---------------------------------------------------------------------------
# Regression — broader contract, error path, and data-quality checks
# ---------------------------------------------------------------------------

@pytest.mark.regression
def test_create_post(base_url):
    """POST /posts returns 201 and the created resource body."""
    payload = {"title": "test post", "body": "test body", "userId": 1}
    response = _post(base_url, "/posts", json=payload)
    created = _assert_json_response(response, 201)
    assert "id" in created
    assert isinstance(created["id"], int)
    assert created["title"] == payload["title"]
    assert created["userId"] == payload["userId"]


@pytest.mark.regression
def test_get_nonexistent_post_returns_404(base_url):
    """Requesting a post that does not exist returns 404."""
    response = _get(base_url, "/posts/99999")
    body = _assert_json_response(response, 404)
    assert isinstance(body.get("detail"), str)
    assert body["detail"].strip()


@pytest.mark.regression
def test_content_type_header(base_url):
    """Responses carry an application/json Content-Type header."""
    response = _get(base_url, "/posts")
    assert "application/json" in response.headers.get("content-type", "")


@pytest.mark.regression
def test_get_users_returns_list(base_url):
    """GET /users returns a list of user objects with required fields."""
    response = _get(base_url, "/users")
    users = _assert_json_response(response, 200)
    assert isinstance(users, list)
    assert len(users) >= 1
    for field in ("id", "name", "email"):
        assert field in users[0]
    assert "@" in users[0]["email"]


@pytest.mark.regression
def test_filter_todos_by_completed(base_url):
    """GET /todos?completed=true returns only completed todos."""
    response = _get(base_url, "/todos", params={"completed": "true"})
    todos = _assert_json_response(response, 200)
    assert isinstance(todos, list)
    assert len(todos) >= 1
    assert all(t["completed"] is True for t in todos)


@pytest.mark.regression
def test_get_nonexistent_user_returns_404(base_url):
    """Negative: requesting an unknown user id should return not found."""
    response = _get(base_url, "/users/99999")
    body = _assert_json_response(response, 404)
    assert isinstance(body.get("detail"), str)
    assert body["detail"].strip()


@pytest.mark.regression
def test_filter_posts_by_unknown_user_returns_empty_list(base_url):
    """Edge: filtering by a non-existent user should return an empty list, not an error."""
    response = _get(base_url, "/posts", params={"userId": 99999})
    posts = _assert_json_response(response, 200)
    assert isinstance(posts, list)
    assert posts == []