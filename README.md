![Tests](https://github.com/KatherLab/llmaixweb/actions/workflows/tests.yml/badge.svg?branch=main)

# LLMAIx (v2) Web

Provides a web interface for the LLMAIx framework, allowing users to interact with the library through a user-friendly interface.


## Get started

**Initialize Users**
```bash
python -m backend.scripts.populate_users
```

**Install Minio**

Start on MacOS:
```bash
minio server miniodata
```

## Development

**Run Backend Tests**
```bash
ENV_PATH=backend/.env uv run pytest
--cov=backend --cov-report=html
```