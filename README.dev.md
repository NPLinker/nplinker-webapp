# `nplinker webapp` developer documentation

If you're looking for user documentation, go [here](README.md).

## Code editor
We use [Visual Studio Code (VS Code)](https://code.visualstudio.com/) as code editor.
The VS Code settings for this project can be found in [.vscode](.vscode).
The settings will be automatically loaded and applied when you open the project with VS Code.
See [the guide](https://code.visualstudio.com/docs/getstarted/settings) for more info about workspace settings of VS Code.


## Setup

```shell
# Create a virtual environment, e.g. with
python3 -m venv venv

# activate virtual environment
source venv/bin/activate

# make sure to have a recent version of pip and setuptools
python3 -m pip install --upgrade pip setuptools

# install webapp dev dependencies
pip install -r requirements.dev.txt

# install nplinker non-pypi dependecies
install-nplinker-deps
```

Afterwards check that the install directory is present in the `PATH` environment variable.

## Linting and formatting


We use [prospector](https://pypi.org/project/prospector/) for linting, [isort](https://pycqa.github.io/isort/) to sort imports, [autoflake](https://github.com/PyCQA/autoflake) to remove unused imports, and [yapf](https://github.com/google/yapf) for formatting, i.e. fixing readability of your code style.

Running the linters and formatters requires an activated virtual environment with the development tools installed.

```shell
# linting
prospector --profile .prospector.yml

# check import style for the project
isort --check .

# check import style and show any proposed changes as a diff
isort --check --diff .

# sort imports for the project
isort .

# remove unused imports for the project
# WARNING: python keyword `pass` will also be removed automatically
autoflake --in-place --remove-all-unused-imports  -r .

# format python style for the project
yapf -r -i .

# format python styple for specific python file
yapf -i filename.py
```

**Note:** We have set linter and formatter in VS Code [settings](.vscode),
so if you're using VS Code, you can also use its shortcut to do linting, sorting and formatting.
Besides, docstring style is also set, you can use [autoDocString](https://marketplace.visualstudio.com/items?itemName=njpwerner.autodocstring) to automatically generate docstrings.


## Versioning

Bumping the version across all files is done with [bumpversion](https://github.com/c4urself/bump2version), e.g.

```shell
bumpversion major
bumpversion minor
bumpversion patch

bumpversion --current-version 0.1.0 --new-version 0.2.0 fakepart
```

## Making a release

This section describes how to make a release in 3 parts:

1. preparation
2. making a release on GitHub

### (1/2) Preparation

1. Update the <CHANGELOG.md> (don't forget to update links at bottom of page)
2. Verify that the information in `CITATION.cff` is correct, and that `.zenodo.json` contains equivalent data
3. Make sure the [version has been updated](#versioning).

### (2/2) GitHub

Make a [release on GitHub](https://github.com/NPLinker/webapp/releases/new). If your repository uses the GitHub-Zenodo integration this will also trigger Zenodo into making a snapshot of your repository and sticking a DOI on it.
