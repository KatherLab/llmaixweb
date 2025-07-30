![Tests](https://github.com/KatherLab/llmaixweb/actions/workflows/tests.yml/badge.svg?branch=main)

# LLMAIx (v2) Web

![cover.png](static/cover.png)

Provides a web interface for the LLMAIx framework, allowing users to interact with the library through a user-friendly interface.


## Features

![img.png](static/features.png)

## Docker Installation


Setup the environment variables in `.env` file:
```bash
cp `.env.example` to `.env` and set the environment variables as needed.
```

Build the Docker image:

```
# GPU stack (requires NVIDIA driver + container toolkit)
docker compose -f docker-compose.gpu.yml up -d --build

# CPU stack
docker compose -f docker-compose.cpu.yml up -d --build
```

Create the database and populate it with initial users (interactive):
```bash
## REPLACE `docker-compose.gpu.yml` with `docker-compose.cpu.yml` for CPU stack
# Currently running stack
docker compose -f docker-compose.gpu.yml exec -it backend python -m backend.scripts.populate_users

# For a currently stopped stack, run:
docker compose -f docker-compose.gpu.yml run --rm -it backend python -m backend.scripts.populate_users
```


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