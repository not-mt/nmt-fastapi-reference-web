# nmt-fastapi-reference-web

[![codecov](https://codecov.io/github/not-mt/nmt-fastapi-reference-web/branch/main/graph/badge.svg)](https://codecov.io/github/not-mt/nmt-fastapi-reference-web)

A FastAPI-based web interface which leverages the `nmtfast` Python package for structured access control, logging, and caching.

## Features

- **OAuth 2.0 & API Key Authentication**: Secure endpoints using `nmtfast`'s authentication and authorization methods.
- **Role-Based & Resource-Based ACLs**: Fine-grained access control managed via YAML configurations, supporting locally defined API keys as well as external identity providers.
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

For local testing, you probably only need to generate an API key. A utility is included with this project to generate password hashes:

```bash
./generate-api-hash.py
```

Place the generated hash in the `nmtfast-config-local.yaml` config file; for example:

```yaml
---
version: 1

auth:
  swagger_token_url: https://some.domain.tld/api/oidc/token
  id_providers: {}
  incoming:
    clients: {}
    api_keys:
      some_key:
        contact: some.user@domain.tld
        memo: This is just some API key
        algo: argon2
        hash: '$argon2id$v=19$m=65536,t=3,p=4$tWmX...'
        acls:
          - section_regex: '^widgets$'
            #permissions: ['*']
            permissions: ['create', 'read']

logging:
  level: DEBUG
  loggers:
    "some.other.module.*":
      level: INFO
```


### Running the Service

You may run the service using a command like this:

```bash
export APP_CONFIG_FILES="./nmtfast-config-local.yaml"
poetry run uvicorn app.main:app --reload
```

**OPTIONAL:** If Docker is available, you may run the service like this:

```bash
cp samples/docker-compose.yaml .
docker-compose build
docker-compose up
```

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

Copyright (c) 2025 Alexander Haye
