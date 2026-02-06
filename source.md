# Source
This file will provide instructions for runnign the application from source. Many of the block commands can also be ran via `npm run ...` if you are unable to copy paste from this file.

```bash
git clone https://github.com/HDTHREE/bintrong_game.git
cd bintrong_game
```

## Creating an environment 
The bearcat game services relies on python and node.
* [`uv`](https://docs.astral.sh/uv/getting-started/installation/) is used to manage python dependencies and version.
* [`nvm`](https://github.com/nvm-sh/nvm?tab=readme-ov-file#installing-and-updating) is used to manage node version (i.e. [`npm`](https://github.com/nvm-sh/nvm?tab=readme-ov-file#nvmrc) from [.nvmrc](./.nvmrc)).

Run the following commands to create the environment:
```bash
uv sync --all-extras
source .venv/bin/activate
# You may need to use a different `.venv/bin/activate.ext` depending on shell.
```
*This can also be ran via `npm run install:venv`.*


## Hosting
The individual services the applciation uses can be ran outside of a kubernetes environment by running from source.


### Database
The application can run on any compatible sqlalchemy connection that supports [an `sqlalchemy` async dialect](https://docs.sqlalchemy.org/en/21/orm/extensions/asyncio.html). The easiest way is to use a file database via sqlite (i.e. `SQL_URL=sqlite+aiosqlite:///my_database.db`). This will result in a database in a file being created on the API machine at `my_database.db`. Additional, packages may be required for other engines. For example, `postgresql+asyncpg://...` requires `asyncpg` be added to the environment. Ensure you set the environment variable `SQL_URL` on the machine running the database.


### File Storage
If no file storage is configured then a binary postgres table can be used. Thus, if you are using postgres you don't need to configure file storage. Otherwise, an S3 storage session can be used by setting the environment variables `S3_URL`, `BUCKET_NAME` and `S3_REGION`.

### SGlang
SGlang requires first a model be installed (mounted if containerized).
The easiest way to do this is through [huggingface](https://huggingface.co/).
Run the following to download the model:
```bash
mkdir -p models/mistral-7b 
uvx --from huggingface_hub hf download mistralai/Mistral-7B-Instruct-v0.3 --local-dir ./models/mistral-7b
```
*This can also be ran via `npm run install:mistral`.*

The following command can be used to start [slang](https://docs.sglang.io/get_started/install.html) instance:
```bash
# This assumes you have the environment activated.
python -m sglang.launch_server \
    --model /models/mistral-7b \
    --context-length 32000 \
    --tp 1 \
    --quantization fp8 \
    --kv-cache-dtype fp8_e5m2 \
    --attention-backend triton \
    --chunked-prefill-size 4096 \
    --mem-fraction-static 0.8 \
    --enable-torch-compile \
    --host 0.0.0.0 \
    --port 30000
```
*This can also be ran via `npm run dev:sgl`.*

```bash
# The following command can be used to run the server in a container using docker.
docker run \
    --interactive \
    --tty
    --detach \
    --publish 30000:30000 \
    --shm-size 32g \
    --gpus all \
    --volume $(pwd)/models/mistral-7b:/local/mistral-7b:ro \
    --ipc=host \
    --privileged \
    --name sglang lmsysorg/sglang:dev \
    python -m sglang.launch_server \
        --model /local/mistral-7b \
        --context-length 32000 \
        --tp 1 \
        --quantization fp8 \
        --kv-cache-dtype fp8_e5m2 \
        --attention-backend triton \
        --chunked-prefill-size 4096 \
        --mem-fraction-static 0.8 \
        --enable-torch-compile \
        --host 0.0.0.0 \
        --port 30000
```
*This can also be ran via `npm run docker:sgl`.*

### Backend
Requires the following environment variables be set: `SGLANG_URL`, `SQL_URL`, `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` and `REFRESH_TOKEN_EXPIRE_DAYS`.

If you are not using postgres then S3 storage must be configured by setting `S3_URL`, `BUCKET_NAME` and `S3_REGION`.


### Frontend
Requires the following environment variables be set: `BACKEND_URL`.


### Running Tests
Tests can simply be ran with `pytest`.
