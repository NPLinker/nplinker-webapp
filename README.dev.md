# `nplinker webapp` developer documentation

If you're looking for user documentation, go [here](README.md).

## Code editor

The VS Code Profile for this project is [vscode/nplinker.code-profile](vscode/nplinker.code-profile), 
which contains the settings, extensions and snippets for the project. To use the profile, you must
first import it by clicking the following menus: `Code` -> `Settings` -> `Profiles` -> `Import Profile...`. 
Then select the file [vscode/nplinker.code-profile](vscode/nplinker.code-profile) to import the profile.
VS Code will take a while to install the extensions and apply the settings. Want more info? See 
[vscode profiles guide](https://code.visualstudio.com/docs/editor/profiles).

If you want to add more settings, you can update the workspace settings, see [the guide](https://code.visualstudio.com/docs/getstarted/settings) for more info.

## Setup

We use Python 3.10 for development environment.

```shell
# Create a virtual environment, e.g. with
python3 -m venv venv

# activate virtual environment
source venv/bin/activate

# make sure to have a recent version of pip and setuptools
python3 -m pip install --upgrade pip setuptools

# install webapp dependencies
pip install -r requirements.dev.txt

#TBD
```

## Running the tests

```shell
pytest
# or
pytest tests
```

### Test coverage

In addition to just running the tests to see if they pass, they can be used for coverage statistics, i.e. to determine how much of the webapp's code is actually executed during tests.
In an activated virtual environment with the development tools installed, inside the webapp's directory, run:

```shell
coverage run
```

This runs tests and stores the result in a `.coverage` file.
To see the results on the command line, run

```shell
coverage report
```

`coverage` can also generate output in HTML and other formats; see `coverage help` for more information.

## Linting and formatting

We use [ruff](https://docs.astral.sh/ruff/) for linting, sorting imports and formatting code. The configurations of `ruff` are set in [ruff.toml](ruff.toml) file.

Running the linters and formatters requires an activated virtual environment with the development tools installed.

```shell
# Lint all files in the current directory.
ruff check .

# Lint all files in the current directory, and fix any fixable errors.
ruff check . --fix

# Format all files in the current directory
ruff format .

# Format a single python file
ruff format filename.py
```

## Static typing

We use [inline type annotation](https://typing.readthedocs.io/en/latest/source/libraries.html#how-to-provide-type-annotations) for static typing rather than stub files (i.e. `.pyi` files).

By default, we use `from __future__ import annotations` at module level to stop evaluating annotations at function definition time (see [PEP 563](https://peps.python.org/pep-0563/)), which would solve most of compatibility issues between different Python versions. Make sure you're aware of the [caveats](https://mypy.readthedocs.io/en/stable/runtime_troubles.html#future-annotations-import-pep-563).

We use [Mypy](http://mypy-lang.org/) as static type checker:

```
# install mypy
pip install mypy

# run mypy
mypy path-to-source-code
```

Mypy configurations are set in [mypy.ini](mypy.ini) file.

For more info about static typing and mypy, see:
- [Static typing with Python](https://typing.readthedocs.io/en/latest/index.html#)
- [Mypy doc](https://mypy.readthedocs.io/en/stable/)
