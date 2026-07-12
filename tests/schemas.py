"""JSON Schema definitions for the resources exposed by the QA portfolio API.

These are validated with ``jsonschema.validate()`` in the test suite in place
of ad hoc ``field in dict`` checks. Shapes were confirmed against live
responses from https://qa-portfolio-api.onrender.com (see e.g. GET /users/1,
GET /posts/1, GET /todos, GET /albums) since the API's own /openapi.json
declares response bodies as loosely-typed ``additionalProperties: true``
objects and doesn't describe the real field-level contract.

``additionalProperties: False`` is used deliberately (stricter than the
API's own OpenAPI doc) so that these schemas actually catch contract drift
-- an unexpected new/missing field will fail validation instead of being
silently ignored.
"""

# A pragmatic "looks like an email" check without requiring the optional
# `jsonschema[format]` / `email-validator` extras just to validate a string.
_EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


POST_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "userId": {"type": "integer"},
        "title": {"type": "string"},
        "body": {"type": "string"},
    },
    "required": ["id", "userId", "title", "body"],
    "additionalProperties": False,
}

COMMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "postId": {"type": "integer"},
        "name": {"type": "string"},
        "email": {"type": "string", "pattern": _EMAIL_PATTERN},
        "body": {"type": "string"},
    },
    "required": ["id", "postId", "name", "email", "body"],
    "additionalProperties": False,
}

TODO_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "userId": {"type": "integer"},
        "title": {"type": "string"},
        "completed": {"type": "boolean"},
    },
    "required": ["id", "userId", "title", "completed"],
    "additionalProperties": False,
}

ALBUM_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "userId": {"type": "integer"},
        "title": {"type": "string"},
    },
    "required": ["id", "userId", "title"],
    "additionalProperties": False,
}

_GEO_SCHEMA = {
    "type": "object",
    "properties": {
        "lat": {"type": "string"},
        "lng": {"type": "string"},
    },
    "required": ["lat", "lng"],
    "additionalProperties": False,
}

_ADDRESS_SCHEMA = {
    "type": "object",
    "properties": {
        "street": {"type": "string"},
        "suite": {"type": "string"},
        "city": {"type": "string"},
        "zipcode": {"type": "string"},
        "geo": _GEO_SCHEMA,
    },
    "required": ["street", "suite", "city", "zipcode", "geo"],
    "additionalProperties": False,
}

_COMPANY_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "catchPhrase": {"type": "string"},
        "bs": {"type": "string"},
    },
    "required": ["name", "catchPhrase", "bs"],
    "additionalProperties": False,
}

USER_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"},
        "username": {"type": "string"},
        "email": {"type": "string", "pattern": _EMAIL_PATTERN},
        "address": _ADDRESS_SCHEMA,
        "phone": {"type": "string"},
        "website": {"type": "string"},
        "company": _COMPANY_SCHEMA,
    },
    "required": [
        "id",
        "name",
        "username",
        "email",
        "address",
        "phone",
        "website",
        "company",
    ],
    "additionalProperties": False,
}


def list_of(item_schema: dict) -> dict:
    """Wrap an item schema into a "list of that item" schema.

    Kept as a small helper so tests can validate list endpoints
    (e.g. GET /posts) with the same per-item schemas defined above,
    without duplicating an array wrapper for every resource.
    """
    return {"type": "array", "items": item_schema}
