# API Testing

This repository contains Python-based API tests against the deployed QA portfolio backend.

## Setup

1. Ensure you have Python 3.8+ installed.
2. Install dependencies:
   ```bash
   pip install -e .
   ```
3. Run the tests:
   ```bash
   pytest
   ```

The default target is the Render-hosted backend at `https://qa-portfolio-api.onrender.com`. Override `BASE_URL` if you want to point the suite at a local or alternate environment.

## Project Structure

- `tests/`: Contains test files
- `pyproject.toml`: Project configuration and dependencies