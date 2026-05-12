import pytest
import requests


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
    response = requests.get(f"{base_url}/health")
    body = _assert_json_response(response, 200)
    assert body["status"] == "ok"


@pytest.mark.smoke
def test_get_posts_returns_list(base_url):
    """GET /posts returns a non-empty list of posts with the expected fields."""
    response = requests.get(f"{base_url}/posts")
    posts = _assert_json_response(response, 200)
    assert isinstance(posts, list)
    assert len(posts) >= 1
    for field in ("id", "userId", "title", "body"):
        assert field in posts[0]


@pytest.mark.smoke
def test_get_single_post(base_url):
    """GET /posts/1 returns the correct resource."""
    response = requests.get(f"{base_url}/posts/1")
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
    response = requests.post(f"{base_url}/posts", json=payload)
    created = _assert_json_response(response, 201)
    assert "id" in created
    assert isinstance(created["id"], int)
    assert created["title"] == payload["title"]
    assert created["userId"] == payload["userId"]


@pytest.mark.regression
def test_get_nonexistent_post_returns_404(base_url):
    """Requesting a post that does not exist returns 404."""
    response = requests.get(f"{base_url}/posts/99999")
    assert response.status_code == 404
    assert response.headers.get("content-type", "").startswith("application/json")
    assert response.json()["detail"]


@pytest.mark.regression
def test_content_type_header(base_url):
    """Responses carry an application/json Content-Type header."""
    response = requests.get(f"{base_url}/posts")
    assert "application/json" in response.headers.get("content-type", "")


@pytest.mark.regression
def test_get_users_returns_list(base_url):
    """GET /users returns a list of user objects with required fields."""
    response = requests.get(f"{base_url}/users")
    users = _assert_json_response(response, 200)
    assert isinstance(users, list)
    assert len(users) >= 1
    for field in ("id", "name", "email"):
        assert field in users[0]
    assert "@" in users[0]["email"]


@pytest.mark.regression
def test_filter_todos_by_completed(base_url):
    """GET /todos?completed=true returns only completed todos."""
    response = requests.get(f"{base_url}/todos", params={"completed": "true"})
    todos = _assert_json_response(response, 200)
    assert isinstance(todos, list)
    assert len(todos) >= 1
    assert all(t["completed"] is True for t in todos)