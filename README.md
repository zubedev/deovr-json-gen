```text
██████╗ ███████╗ ██████╗ ██╗   ██╗██████╗            ██╗███████╗ ██████╗ ███╗   ██╗       ██████╗ ███████╗███╗   ██╗
██╔══██╗██╔════╝██╔═══██╗██║   ██║██╔══██╗           ██║██╔════╝██╔═══██╗████╗  ██║      ██╔════╝ ██╔════╝████╗  ██║
██║  ██║█████╗  ██║   ██║██║   ██║██████╔╝█████╗     ██║███████╗██║   ██║██╔██╗ ██║█████╗██║  ███╗█████╗  ██╔██╗ ██║
██║  ██║██╔══╝  ██║   ██║╚██╗ ██╔╝██╔══██╗╚════╝██   ██║╚════██║██║   ██║██║╚██╗██║╚════╝██║   ██║██╔══╝  ██║╚██╗██║
██████╔╝███████╗╚██████╔╝ ╚████╔╝ ██║  ██║      ╚█████╔╝███████║╚██████╔╝██║ ╚████║      ╚██████╔╝███████╗██║ ╚████║
╚═════╝ ╚══════╝ ╚═════╝   ╚═══╝  ╚═╝  ╚═╝       ╚════╝ ╚══════╝ ╚═════╝ ╚═╝  ╚═══╝       ╚═════╝ ╚══════╝╚═╝  ╚═══╝
>---------------------------------------------------------------------------------------------- DeoVR JSON Generator
```

[![python](https://img.shields.io/badge/python-3.11-%233776AB?style=flat-square&logo=python)](https://www.python.org)
[![mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org)
[![black](https://img.shields.io/badge/code%20style-black-black.svg?style=flat-square&logo=stylelint)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?style=flat-square&logo=pre-commit)](https://pre-commit.com)
[![license](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/zubedev/deovr-json-gen/actions/workflows/ci.yml/badge.svg)](https://github.com/zubedev/deovr-json-gen/actions/workflows/ci.yml)

## Usage

```bash
# Copy the example environment file to .env
# Set DEOVR_JSON_GEN_URL to the URL of your domain (if any), else
# Change the WEB_HOST value to your IP address
cp .env.example .env

# Create an empty deovr file on project root
touch deovr

# Build the docker image and run the container
docker-compose up --build --detach
```
Site is now available at http://<WEB_HOST>:<WEB_PORT> (http://localhost:32169 by default) - host and port can be changed in `.env`.

Using a DeoVR player on your VR headset browse to the above URL and you should see your VR directory listed.

## Development

```bash
# Poetry is required for installing and managing dependencies
# https://python-poetry.org/docs/#installation
poetry install

# Run the generator locally
poetry run python main.py </path/to/your/vr/directory>

# Install pre-commit hooks
poetry run pre-commit install

# Formatting (inplace formats code)
poetry run black .

# Linting (and to fix automatically)
poetry run ruff .
poetry run ruff --fix .

# Type checking
poetry run mypy .
```

Configuration details can be found in [pyproject.toml](pyproject.toml).

## Support
[![Paypal](https://img.shields.io/badge/Paypal-@MdZubairBeg-253B80?&logo=paypal)](https://paypal.me/MdZubairBeg/10)
