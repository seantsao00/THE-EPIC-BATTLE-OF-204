# THE-EPIC-BATTLE-OF-204

A LLM-driven DNS firewall and moderation API for college final project use.

## Quick Start

1. **Set up environment variables**

    Create a `.env` file with at least:

    ```env
    OPENAI_API_KEY=your_openai_key
    ```

    And optionally:

    ```env
    DNS_IP=127.0.0.1
    DNS_PORT=5353
    API_IP=127.0.0.1
    API_PORT=8000
    SECRET_KEY=your_secret_key
    SQLALCHEMY_DATABASE_URL=sqlite:///./db.sqlite3
    CLAM_URL=cool.ntu.edu.tw
    ```

1. **Initialize admin user**

    ```sh
    uv run init_admin.py
    ```

1. **Run the server**

    This project uses [uv](https://github.com/astral-sh/uv) for fast Python dependency management. After cloning the repo, run:

    ```sh
    uv run uvicorn app.main:app --reload
    ```

    This will install all dependencies locked in `uv.lock` and start the server.

## Notes

- API docs available at `/docs` when running.

---
