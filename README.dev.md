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

We use Python 3.10 for development.

```shell
# Create a virtual environment, e.g. with
python3.10 -m venv venv

# activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# make sure to have a recent version of pip and setuptools
python -m pip install --upgrade pip setuptools

# install all dependencies (including development dependencies)
pip install -e ".[dev]"

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
# run mypy (already installed as a dev dependency)
mypy path-to-source-code
```

Mypy configurations are set in [mypy.ini](mypy.ini) file.

For more info about static typing and mypy, see:
- [Static typing with Python](https://typing.readthedocs.io/en/latest/index.html#)
- [Mypy doc](https://mypy.readthedocs.io/en/stable/)

## Branching workflow

We use a [Git Flow](https://nvie.com/posts/a-successful-git-branching-model/)-inspired branching workflow for development. This repository is based on two main branches with infinite lifetime:

- `main` — this branch contains production (stable) code. All development code is merged into `main` in sometime.
- `dev` — this branch contains pre-production code. When the features are finished then they are merged into `dev`.

During the development cycle, three main supporting branches are used:

- Feature branches - Branches that branch off from `dev` and must merge into `dev`: used to develop new features for the upcoming releases.
- Hotfix branches - Branches that branch off from `main` and must merge into `main` and `dev`: necessary to act immediately upon an undesired status of `main`.
- Release branches - Branches that branch off from `dev` and must merge into `main` and `dev`: support preparation of a new production release. They allow many minor bug to be fixed and preparation of meta-data for a release.

## GitHub release

0. Make sure you have all required developers tools installed `pip install -e .'[test]'`.
1. Create a `release-` branch from `main` (if there has been an hotfix) or `dev` (regular new production release).
2. Prepare the branch for release by ensuring all tests pass (`pytest -v`), and that linting (`ruff check`), formatting (`ruff format --check`) and static typing (`mypy app tests`) rules are adhered to. Make sure that the debug mode in the `app/main.py` file is set to `False`.
3. Merge the release branch into both `main` and `dev`.
4. On the [Releases page](https://github.com/neurogym/neurogym/releases):
   1. Click "Draft a new release"
   2. By convention, use `v<version number>` as both the release title and as a tag for the release. Decide on the [version level increase](#versioning), following [semantic versioning conventions](https://semver.org/) (MAJOR.MINOR.PATCH).
   3. Click "Generate release notes" to automatically load release notes from merged PRs since the last release.
   4. Adjust the notes as required.
   5. Ensure that "Set as latest release" is checked and that both other boxes are unchecked.
   6. Hit "Publish release".
      - This will automatically trigger a [GitHub workflow](https://github.com/NPLinker/nplinker-webapp/blob/main/.github/workflows/release_ghcr.yml) that will take care of updating the version number in the relevant files and publishing the image of the dashboard to the GitHub Container Registry.
