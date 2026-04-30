# nmt-fastapi-reference-web

[![codecov](https://codecov.io/github/not-mt/nmt-fastapi-reference-web/branch/main/graph/badge.svg)](https://codecov.io/github/not-mt/nmt-fastapi-reference-web)

A FastAPI-based web interface (BFF — Backend for Frontend) that provides an HTMX-driven UI for the [nmt-fastapi-reference](https://github.com/not-mt/nmt-fastapi-reference) API. Leverages the `nmtfast` Python package for reusable authentication, templates, and data-driven CRUD components.

## Features

- **HTMX-Powered Web UI**: Data-driven CRUD interface using HTMX, Jinja2, and Tailwind CSS — no JavaScript framework required.
- **SSO / OAuth 2.0 Login**: Interactive user authentication via OpenID Connect, with session management and cookie-based sessions.
- **Data-Driven Resource Management**: Reusable template system driven by `ResourceConfig` — define fields, accents, and layouts in Python, rendered automatically by shared templates.
- **Backend for Frontend (BFF)**: Proxies API calls to the upstream reference API, handling token forwarding, error presentation, and response transformation.
- **Backend Integration**:
  - **Redis**: Used for caching, deduplication, and ephemeral state.
  - **MongoDB**: Async document storage using Motor for high-performance NoSQL access.
  - **Kafka**: Async event streaming with aiokafka for producer and consumer support.
- **Asynchronous API Handling**: Fully async stack using FastAPI, MongoDB, and Kafka async drivers.
- **Structured Logging**: Per-request unique IDs, configurable logger hierarchy, and customizable log formatters.
- **Docker Examples**: Easily deployable with a multi-stage `Dockerfile` and a sample `docker-compose.yaml` for local development.
- **Merged Configuration Files**: Declarative YAML-based configuration merged in layers (shared defaults, environment overrides, secrets) with full support for SOPS-encrypted values.

## Getting Started

### Prerequisites

- Python 3.11+
- MongoDB database
- Redis

### Prepare Development Environment

Clone the repository and install dependencies using Poetry:

```bash
git clone https://github.com/not-mt/nmt-fastapi-reference-web.git
cd nmt-fastapi-reference-web
```

Create a virtual environment and install Poetry:

```bash
test -d .venv || python -m venv .venv
source .venv/Scripts/activate
pip install poetry
cp samples/poetry.toml .
```

Install dependencies:

```bash
poetry install
```

Install pre-commit:

```bash
pre-commit install
```

### OPTIONAL: VS Code (on Windows)

Follow these steps if you are developing on a Windows system and have a bash shell available (most likely from [Git for Windows](https://git-scm.com/downloads/win)).

Copy samples:

```bash
cp -urv samples/{.local,.vscode,*} .
```

These files will be excluded by `.gitignore`, and you may customize however you would like. These are the notable files:

- **.local/activate.env**
  - This file will be sourced in a custom terminal profile (defined in `nmt-fastapi-reference-web.code-workspace` )
  - Customize `PROJECTS` to reflect the root path to your software projects
- **.vscode/launch.json**
  - Template of how to start the project in VS Code's debugger; adjust if necessary
- **nmt-fastapi-reference-web.code-workspace**
  - Sensible defaults are specified here and may be customized as necessary
  - A `terminal.integrated.defaultProfile.windows` is set to use the `.local/activate.env` file when starting new terminals

**NOTE:** You can update `PROJECTS` in `.local/activate.env` file manually, or you can use this command to update it for you. This will set the value to the parent directory of your current directory:

```bash
# get the parent directory, and replace /c/path with C:/path
rpd=$(dirname "$(pwd)" | sed -E 's|^/([a-z])|\U\1:|')
sed \
  -e 's|# export PROJECTS=".*FIXME.*$|export PROJECTS="'"$rpd"'"|' \
  -i .local/activate.env
```

Test the activate script:

```bash
source .local/activate.env
```

Once files have been customized, you may re-open VS Code using the `nmt-fastapi-reference-web.code-workspace` file.

### Configuration

This service is configured using YAML configuration files. You may copy the `nmtfast-config-default.yaml` and update as necessary:

```bash
cp nmtfast-config-default.yaml nmtfast-config-local.yaml
$EDITOR nmtfast-config-local.yaml
```

#### Architecture

This application is a **web UI frontend** (BFF — Backend for Frontend) that communicates with the [nmt-fastapi-reference](https://github.com/not-mt/nmt-fastapi-reference) API as its upstream backend. You must have the reference API running and reachable before starting this service.

```
Browser  →  nmt-fastapi-reference-web (this app)  →  nmt-fastapi-reference (API)
              ↕ SSO / OIDC Provider
```

#### Upstream API Connection

Configure the URL of the running reference API instance:

```yaml
upstream:
  reference_api:
    url: http://localhost:8005
```

#### Authentication (SSO / OIDC)

The web UI uses OAuth 2.0 / OpenID Connect for interactive user login. You need an OIDC provider (e.g. [Authelia](https://www.authelia.com/), [Keycloak](https://www.keycloak.org/), or any compliant provider).

Configure the identity provider, web auth client, and session settings:

```yaml
auth:
  id_providers:
    my_provider:
      type: jwks
      issuer_regex: '^https://auth\.example\.com'
      jwks_endpoint: https://auth.example.com/jwks.json
      token_endpoint: https://auth.example.com/api/oidc/token
      authorize_endpoint: https://auth.example.com/api/oidc/authorization
      introspection_enabled: false

  incoming:
    clients:
      web_ui_client:
        contact: admin@example.com
        memo: Web UI interactive login client
        provider: my_provider
        claims:
          azp: nmt-fastapi-reference-web
        acls: []

  web_auth:
    provider: my_provider
    client_id: nmt-fastapi-reference-web
    client_secret: your-client-secret-here
    redirect_uri: http://localhost:8000/ui/v1/auth/callback
    scopes:
      - openid
      - profile
      - email
      - groups
    pkce_enabled: false
    refresh_enabled: false
    token_endpoint_auth_method: client_secret_post
    displayname_claims:
      - preferred_username
      - mail
    userid_claims:
      - sub

  session:
    cookie_name: session_id
    cookie_secure: false      # set to true in production (requires HTTPS)
    cookie_httponly: true
    cookie_samesite: lax
    cookie_path: /
    session_ttl: 3600
```

#### API Key Authentication (for the upstream API)

If the upstream reference API requires authentication, configure an outgoing client or static headers so this service can authenticate its API calls:

```yaml
auth:
  outgoing:
    headers:
      upstream_headers:
        contact: admin@example.com
        memo: Static API key for upstream reference API
        headers:
          X-API-Key: your-api-key-here
```

#### Logging

```yaml
logging:
  level: DEBUG
  loggers:
    "aiosqlite":
      level: INFO
    "pymongo":
      level: INFO
```

#### Minimal Working Example

A minimal `nmtfast-config-local.yaml` for local development (assuming the reference API is running on port 8005 and an OIDC provider is available):

```yaml
---
version: 1

upstream:
  reference_api:
    url: http://localhost:8005

auth:
  id_providers:
    my_provider:
      type: jwks
      issuer_regex: '^https://auth\.example\.com'
      jwks_endpoint: https://auth.example.com/jwks.json
      token_endpoint: https://auth.example.com/api/oidc/token
      authorize_endpoint: https://auth.example.com/api/oidc/authorization
  incoming:
    clients:
      web_ui_client:
        contact: admin@example.com
        memo: Web UI interactive login
        provider: my_provider
        claims:
          azp: nmt-fastapi-reference-web
        acls: []
  outgoing:
    headers:
      upstream_headers:
        contact: admin@example.com
        memo: API key for upstream
        headers:
          X-API-Key: your-api-key-here
  web_auth:
    provider: my_provider
    client_id: nmt-fastapi-reference-web
    client_secret: your-client-secret
    redirect_uri: http://localhost:8000/ui/v1/auth/callback
    scopes: [openid, profile, email, groups]
    token_endpoint_auth_method: client_secret_post
    displayname_claims: [preferred_username, mail]
    userid_claims: [sub]
  session:
    cookie_secure: false
    session_ttl: 3600

logging:
  level: DEBUG
```


### Running the Service

#### Prerequisites

1. **Start the upstream reference API** ([nmt-fastapi-reference](https://github.com/not-mt/nmt-fastapi-reference)) — this web UI requires a running API backend.
2. **Configure an OIDC provider** — the web UI uses SSO for user login (see [Authentication](#authentication-sso--oidc) above).

#### Local Development

```bash
export APP_CONFIG_FILES="./nmtfast-config-local.yaml"
poetry run uvicorn app.main:app --reload --port 8000
```

Then open `http://localhost:8000/ui/v1/login` in your browser.

#### Docker

```bash
cp samples/docker-compose.yaml .
docker-compose build
docker-compose up
```

The containerized service listens on port **8080** (nginx → uvicorn). Open `http://localhost:8080/ui/v1/login` in your browser.

## Invoke Tasks

Invoke is included with this project so that repetitive tasks such as pytest, mypy, etc. can be bundled into simple task names without requiring complex arguments each time. For example, this will check static type hints for the entire project:

```bash
poetry run invoke mypy
```

Run `poetry run invoke --complete` to see all available tasks.

## Testing

Verify all `pre-commit` checks are working:

```bash
pre-commit run --all-files
```

Verify code coverage and unit tests:

```bash
poetry run invoke coverage
```

## Contributing

Contributions are welcome! Please submit a pull request or open an issue.

## License

This project is licensed under the [MIT License](LICENSE).

Copyright (c) 2026 Alexander Haye
