# API Testing

This repository contains Python-based API tests against the deployed QA portfolio backend.

It is designed to be:
- Portfolio-friendly: clear smoke/regression coverage with readable assertions
- Team-friendly: easy to retarget to another environment via configuration

## Setup

1. Ensure you have Python 3.11+ installed.
2. Install dependencies:
   ```bash
   pip install -e .
   ```
3. Run the tests:
   ```bash
   pytest
   ```

The default target is the Render-hosted backend at `https://qa-portfolio-api.onrender.com`. Override `BASE_URL` if you want to point the suite at a local or alternate environment.

## What This Suite Demonstrates

- Contract checks for status, content type, and core response structure
- Happy-path coverage for key resources
- Negative and edge checks (404s, empty filtered sets)
- Explicit request timeouts in test calls for more reliable CI behavior

## Project Structure

- `tests/`: Contains test files
- `pyproject.toml`: Project configuration and dependencies

## Reuse Notes

- Set `BASE_URL` to reuse the suite against another API host
- Keep smoke tests fast and stable; put broader scenarios in regression markers
- Expand assertions with domain-specific schema checks as your API evolves