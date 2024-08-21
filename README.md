# Flamapy Development CLI Tool

This repository provides a command-line interface (CLI) tool for managing Git repositories and Python packages within a project. The tool uses `Click` to offer commands for cloning repositories, managing Git branches, and handling Python dependencies.

## Project Structure

```
flamapy_dev/
│
├── flamapy_dev.py
└── commands/
    ├── git_commands.py
    └── pip_commands.py
```

### `flamapy_dev.py`

The main entry point for the CLI tool. It organizes and provides access to Git and pip commands.

### `commands/git_commands.py`

Contains commands related to Git operations such as cloning repositories, switching branches, pulling updates, and deleting directories.

### `commands/pip_commands.py`

Contains commands for managing Python dependencies by iterating through directories and executing `pip install .`, `pip install --upgrade .`, and `pip uninstall -y .` commands.

## Setup

### Prerequisites

Ensure you have Python 3.6 or higher installed. You also need to install the `Click` package. Install it using pip:

```bash
pip install click
```

### Installation

Clone this repository:

```bash
git clone <repository_url>
cd <repository_directory>
```

## Usage

### Git Commands

The following commands are available for managing Git repositories:

- **Clone Repositories**

  Clones all repositories defined in `git_commands.py` into the parent directory.

  ```bash
  python flamapy_dev.py git clone
  ```

- **Switch to Develop Branch**

  Switches all repositories to the `develop` branch if it exists.

  ```bash
  python flamapy_dev.py git switch_develop
  ```

- **Switch to Main or Master Branch**

  Switches all repositories to the `main` branch if it exists; otherwise, switches to `master`.

  ```bash
  python flamapy_dev.py git switch_main_or_master
  ```

- **Pull Latest Changes**

  Pulls the latest changes from all repositories.

  ```bash
  python flamapy_dev.py git pull
  ```

- **Delete Repositories**

  Deletes all repository directories defined in `git_commands.py`.

  ```bash
  python flamapy_dev.py git delete
  ```

- **Show Status**

  Shows the status of all repositories.

  ```bash
  python flamapy_dev.py git status
  ```

### Pip Commands

The following commands are available for managing Python dependencies:

- **Install Packages**

  Installs packages from `setup.py` in each directory under the parent directory.

  ```bash
  python flamapy_dev.py pip install
  ```

- **Update Packages**

  Updates packages from `setup.py` in each directory under the parent directory.

  ```bash
  python flamapy_dev.py pip update
  ```

- **Remove Packages**

  Uninstalls packages from `setup.py` in each directory under the parent directory.

  ```bash
  python flamapy_dev.py pip remove
  ```

## Configuration

### `commands/git_commands.py`

Define your repositories and parent directory in this file. Update the `REPOS` dictionary with your repositories and set the `PARENT_DIR` to the appropriate directory.

### `commands/pip_commands.py`

Set the `PARENT_DIR` to the parent directory where your Python packages are located. This script will search for `setup.py` files in subdirectories to manage the packages.

## Contributing

Feel free to open issues or submit pull requests for improvements or bug fixes. For detailed contributing guidelines, please refer to the [CONTRIBUTING.md](CONTRIBUTING.md) file.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

This updated `README.md` reflects the new file structure and provides instructions for using the CLI tool organized by the `flamapy_dev.py` script and the command modules within the `commands` directory. Adjust the content as needed based on any additional details or changes in your project.