## Source
This file will provide instructions for runnign the application from source.

```bash
git clone https://github.com/HDTHREE/bintrong_game.git
cd bintrong_game
```

### Creating an environment 
The bearcat game services relies on python and node.
* [`uv`](https://docs.astral.sh/uv/getting-started/installation/) is used to manage python dependencies and version.
* [`nvm`](https://github.com/nvm-sh/nvm?tab=readme-ov-file#installing-and-updating) is used to manage node version (i.e. [`npm`](https://github.com/nvm-sh/nvm?tab=readme-ov-file#nvmrc) from [.nvmrc](./.nvmrc)).

Run the following commands to create the environment:
```bash
uv sync --all-extras
source .venv/bin/activate
# You may need to use a different `.venv/bin/activate.ext` depending on shell.
```


### Hosting
The individual services the applciation uses can be ran outside of a kubernetes environment by running from source.

#### Database
The application can run on any compatible sqlalchemy connection that supports [an `sqlalchemy` async dialect](https://docs.sqlalchemy.org/en/21/orm/extensions/asyncio.html). The easiest way is to use a file database via sqlite (i.e. `SQL_URL=sqlite+aiosqlite:///my_database.db`). This will result in a database in a file being created on the API machine at `my_database.db`. Additional, packages may be required for other engines. For example, `postgresql+asyncpg://...` requires `asyncpg` be added to the environment.


#### SGlang
SGlang requires first a model be installed.



#### Backend


### Running Tests
Tests can simply be ran with `pytest`.
