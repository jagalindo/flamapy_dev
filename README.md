# Flamapy Development CLI Tool

This repository provides a command-line interface (CLI) tool for managing Git repositories and Python packages within a project. The tool uses `Click` to offer commands for cloning repositories, managing Git branches, and handling Python dependencies.

## Project Structure

```
flamapy_dev/
│
├── flamapy_dev.py
└── commands/
    ├── __init__.py
    ├── repositories.py
    ├── packages.py
    ├── make.py
    └── versions.py
```

### `flamapy_dev.py`

The main entry point for the CLI tool. It organizes and provides access to Git, pip, version, and make commands.

### `commands/repositories.py`

Contains commands related to Git operations such as cloning repositories, switching branches, pulling updates, tagging, and deleting directories.

### `commands/packages.py`

Contains commands for managing Python dependencies by iterating through directories and executing `pip install .`, `pip install --upgrade .`, and `pip uninstall -y .` commands.

### `commands/make.py`

Provides commands that run common `make` targets like `lint`, `test`, and `mypy` across all repositories.

### `commands/versions.py`

Offers a command to bump package versions in all repositories and update internal dependencies accordingly.

## Setup

Ensure you have Python 3.6 or higher installed.

Create and activate a new virtual environment:

```bash
python -m venv venv
source venv/bin/activate
```

Then install the CLI tool with pip (this will also install `Click` and any other
dependencies):

```bash
pip install flamapy-dev
```

## Usage

### Git Commands

The following commands are available for managing Git repositories.
Use `--parent-dir PATH` to specify where the repositories are located (defaults to the current directory `.`):

- **Clone Repositories**

  Clones all repositories defined in `repositories.py` into the parent directory.

  ```bash
  flamapy-dev git clone
  ```

- **Switch to Develop Branch**

  Switches all repositories to the `develop` branch if it exists.
  If the branch only exists on the remote, it will be created locally first.

  ```bash
  flamapy-dev git switch_develop
  ```

- **Switch to Main or Master Branch**

  Switches all repositories to the `main` branch if it exists; otherwise, switches to `master`.

  ```bash
  flamapy-dev git switch-main
  ```

- **Pull Latest Changes**

  Fetches and merges the latest commits for each repository.

  ```bash
  flamapy-dev git pull
  ```

- **Delete Repositories**

  Deletes all repository directories defined in `repositories.py`.

  ```bash
  flamapy-dev git delete
  ```

- **Show Status**

  Shows the status of all repositories.

  ```bash
  flamapy-dev git status
  ```

- **Tag Repositories**

  Creates and pushes a Git tag to each repository.

  ```bash
  flamapy-dev git tag v1.0.0
  ```

### Pip Commands

The following commands are available for managing Python dependencies:

- **Install Packages**

  Installs packages from `setup.py` in each directory under the parent directory.

  ```bash
  flamapy-dev pip install
  ```

- **Update Packages**

  Updates packages from `setup.py` in each directory under the parent directory.

  ```bash
  flamapy-dev pip update
  ```

- **Remove Packages**

  Uninstalls packages from `setup.py` in each directory under the parent directory.


  ```bash
  flamapy-dev pip remove
  ```

### Version Commands

- **Bump Version**

  Updates `setup.py` and `requirements.txt` in all repositories to the provided version.

  ```bash
  flamapy-dev version bump 1.2.0
  ```

### Make Commands

Execute common `make` targets for every repository.

- **Lint**

  ```bash
  flamapy-dev make lint
  ```

  Runs `make lint` in each repository.

- **Test**

  ```bash
  flamapy-dev make test
  ```

  Runs `make test` in each repository.

- **Mypy**

  ```bash
  flamapy-dev make mypy
  ```

  Runs static type checking using `make mypy`.

## Configuration

### `commands/repositories.py`

Define your repositories and parent directory in this file. Update the `REPOS` dictionary with your repositories and set the `PARENT_DIR` to the appropriate directory.

### `commands/packages.py`

Set the `PARENT_DIR` to the parent directory where your Python packages are located. This script will search for `setup.py` files in subdirectories to manage the packages.

## Contributing

Feel free to open issues or submit pull requests for improvements or bug fixes. For detailed contributing guidelines, please refer to the [CONTRIBUTING.md](CONTRIBUTING.md) file.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
