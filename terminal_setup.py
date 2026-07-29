#!/usr/bin/env python3
import os
import pwd
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse
import re

HOME = Path.home()
ZSHRC_PATH = HOME / ".zshrc"
OMZ_PATH = HOME / ".oh-my-zsh"
OMZ_SCRIPT_PATH = OMZ_PATH / "oh-my-zsh.sh"
CUSTOM_PLUGIN_PATH = OMZ_PATH / "custom" / "plugins"



# shared functions start here

def ask_yes_no(question: str) -> bool:
    while True:
        answer = input(f"{question} [y/n]: ").strip().lower()

        if answer in ("y", "yes"):
            return True

        if answer in ("n", "no"):
            return False

        print("Please enter y or n.")

def run_command(command: list[str]) -> bool:
    print(f"\nRunning: {' '.join(command)}")

    try:
        subprocess.run(command, check=True)
        return True
    except subprocess.CalledProcessError as error:
        print(f"Command failed with exit code {error.returncode}.")
        return False
    except FileNotFoundError:
        print(f"Command not found: {command[0]}")
        return False

def get_default_shell() -> str:
    user_record = pwd.getpwuid(os.getuid())
    return user_record.pw_shell

def ensure_dependencies(dependencies: dict[str, str]) -> bool:
    missing_dependencies = {
        command:package for command, package in dependencies.items()
        if shutil.which(command) is None
    }

    if not missing_dependencies:
        return True

    missing_packages = sorted(set(missing_dependencies.values()))
    print(f"You are missing: {', '.join(missing_packages)}")    

    if not ask_yes_no("Do you want to install the missing dependencies?"):
        print("Dependency installation skipped.")
        return False

    if not run_command (["sudo", "apt-get", "update"]):
        return False

    if not run_command(["sudo", "apt-get", "install", "-y", *missing_packages]):
        return False

    still_missing = {
        command:package for command, package in missing_dependencies.items()
        if shutil.which(command) is None
    }

    if still_missing:
        print(f"Failed to install: {', '.join(set(still_missing.values()))}")
        return False

    print(f"Successfully installed: {', '.join(missing_packages)}")
    return True

# this is the main function to make sure zsh is installed/default

def ensure_zsh() -> bool:
    zsh_path = shutil.which("zsh")

    if zsh_path is None:
        print("Zsh is not installed.")

        if not ask_yes_no("Do you want to install Zsh?"):
            print("Zsh installation skipped.")
            return False
        if not run_command(["sudo", "apt-get", "update"]):
            return False
        if not run_command(["sudo", "apt-get", "install", "-y", "zsh"]):
            return False
        zsh_path = shutil.which("zsh")

        if zsh_path is None:
            print("Zsh installation failed.")
            return False
        print(f"Zsh installed at {zsh_path}.")
    else:
        print(f"Zsh is already installed at {zsh_path}.")
    default_shell = get_default_shell()
    if os.path.realpath(default_shell) != os.path.realpath(zsh_path):
        print(f"Current default shell is {default_shell}.")
        if ask_yes_no(f"Set your default shell to {zsh_path}?"):
            if run_command(["chsh", "-s", zsh_path]):
                print("Default shell changed.")
                print("Log out and log back in to see changes.")
            else:
                print("Failed to change default shell.")
                return False
    else:
        print("Default shell is already Zsh.")

    return True

# starting here we make sure the script is not run as root, then we call the main function to make sure zsh is installed and set as default

def main() -> int:
    if os.geteuid() == 0:
        print("This script should not be run as root. Please run as a regular user.")
        return 1
    print("Starting terminal setup")
    print("----------------------------")

    if not ensure_zsh():
        print("Zsh setup failed. Please rerun the script and check for errors.")
        print("You can also manually install Zsh and set it as your default shell.")
        return 1
    print("Zsh setup completed successfully.")

    if not ensure_oh_my_zsh():
        print("OMZ setup failed. Please rerun the script and check for errors.")
        print("You can also manually install OMZ.")
        return 1
    
    print("OMZ setup completed successfully.")

    if not manage_plugins():
        print("Plugin setup encountered an error")
        return 1
    
    print("\nTerminal setup completed successfully.")
    return 0

# starting here we check for omz, curl, and git 
def oh_my_zsh_installed() -> bool:
    return OMZ_SCRIPT_PATH.is_file()

def ensure_oh_my_zsh() -> bool:
    installer_path = Path("/tmp/oh-my-zsh-install.sh")
    installer_url = "https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh"

    if oh_my_zsh_installed():
        print(f"OMZ detected at {OMZ_PATH}.")

        if not ZSHRC_PATH.is_file():
            print(f"OMZ exists, but {ZSHRC_PATH} could not be found.")
            return False

        return True

    if OMZ_PATH.exists():
        print(f"An incomplete OMZ directory exists at {OMZ_PATH}.")
        print("Rename or remove it before attempting installation.")
        return False

    
    print("OMZ is not installed.")

    if not ask_yes_no("Do you want to install OMZ?"):
        print("OMZ installation skipped.")
        return False

    if not ensure_dependencies({
        "curl": "curl",
        "git": "git",
    }):
        return False


    installer_path.unlink(missing_ok=True)

    try:
        if not run_command(["curl", "-fsSL", installer_url, "-o", str(installer_path)]):
            return False

        if not run_command(["sh", str(installer_path), "--unattended"]):
            return False
    finally:
        installer_path.unlink(missing_ok=True)

    if not oh_my_zsh_installed():
        print("OMZ installation failed.")
        return False

    if not ZSHRC_PATH.is_file():
        print(f"OMZ was installed, but {ZSHRC_PATH} could not be found.")
        return False

    print(f"OMZ installed at {OMZ_PATH}.")
    return True

#starting here we check for plugins, we have a funciton to clone them, then we append them to zshrc

def get_plugin_name(repository_url: str) -> str | None:
    parsed_url = urlparse(repository_url)
    if parsed_url.scheme != "https":
        return None
    if parsed_url.hostname not in ("github.com", "gitlab.com"):
        return None
    path_parts = parsed_url.path.strip("/").split("/")

    if len(path_parts) != 2:
        return None
    plugin_name = path_parts[1].removesuffix(".git")

    if not plugin_name:
        return None
    return plugin_name

def clone_plugin(repository_url: str, plugin_name: str) -> bool:
    plugin_path = CUSTOM_PLUGIN_PATH / plugin_name

    if plugin_path.exists():
        print(f"Plugin {plugin_name} already exists at {plugin_path}.")
        return True
    print(f"Installing {plugin_name} plugin from {repository_url}")

    if not run_command(["git", "clone", "--depth=1", repository_url, str(plugin_path)]):
        print(f"Failed to clone {plugin_name} plugin.")
        return False

    if not plugin_path.is_dir():
        print("Git completed but plugin directory couldn't be found")
        return False

    print(f"Plugin {plugin_name} installed at {plugin_path}.")
    return True

PLUGIN_BLOCK_PATTERN = re.compile(
    r"^[ \t]*plugins=\((.*?)\)",
    re.MULTILINE | re.DOTALL,
)

def get_enabled_plugins() -> list[str] | None:
    zshrc_text = ZSHRC_PATH.read_text()

    match = PLUGIN_BLOCK_PATTERN.search(zshrc_text)

    if match is None:
        return None

    plugin_block = match.group(1)

    uncommented_lines = []

    for line in plugin_block.splitlines():
        line_without_comment = line.split("#", 1)[0]
        uncommented_lines.append(line_without_comment)
    uncommented_block = "\n".join(uncommented_lines)

    return uncommented_block.split()


def backup_zshrc() -> bool:
    backup_path = HOME / ".zshrc.backup"

    try:
        if not backup_path.exists():
            shutil.copy2(ZSHRC_PATH, backup_path)
            print(f"Backup of .zshrc created at {backup_path}.")
        else:
            print(f"Backup of .zshrc already exists at {backup_path}.")
        return True

    except OSError as error:
        print(f"Failed to create backup of .zshrc: {error}")
        return False

def enable_plugin(plugin_name: str) -> bool:
    enabled_plugins = get_enabled_plugins()

    if enabled_plugins is None:
        print("Could not find plugins block in .zshrc.")
        return False

    if plugin_name in enabled_plugins:
        print(f"Plugin {plugin_name} is already enabled in .zshrc.")
        return True

    try:
        zshrc_text = ZSHRC_PATH.read_text()
    except OSError as error:
        print(f"Failed to read .zshrc: {error}")
        return False

    match = PLUGIN_BLOCK_PATTERN.search(zshrc_text)

    if match is None:
        print("Could not find plugins block in .zshrc.")
        return False

    plugin_block = match.group(1)

    if "\n" in plugin_block:
        new_plugin_block = plugin_block + f"\n  {plugin_name}"
    else:
        existing_plugins = plugin_block.strip()
        new_plugin_block = f"{existing_plugins} {plugin_name}"

    updated_zshrc = (
        zshrc_text[: match.start(1)]
        + new_plugin_block
        + zshrc_text[match.end(1) :]
    )

    if not backup_zshrc():
        return False

    try:
        ZSHRC_PATH.write_text(updated_zshrc)
    except OSError as error:
        print(f"Failed to write updated .zshrc: {error}")
        return False
    if plugin_name not in (get_enabled_plugins() or []):
        print(f"Failed to enable plugin {plugin_name} in .zshrc.")
        return False

    print(f"Plugin {plugin_name} enabled successfully in .zshrc.")
    return True

def install_plugin() -> bool:
    repository_url = input("Enter the plugin repository URL:").strip()

    plugin_name = get_plugin_name(repository_url)

    if plugin_name is None:
        print("Invalid repository URL. Please provide a valid GitHub or GitLab repository URL.")
        return False 

    print(f"Detected plugin name: {plugin_name}")

    if not clone_plugin(repository_url, plugin_name):
        print(f"Failed to install plugin {plugin_name}.")
        return False

    if not enable_plugin(plugin_name):
        print(f"{plugin_name} was installed but could not be enabled in .zshrc.")
        return False

    print(f"Plugin {plugin_name} installed and enabled successfully.")
    return True

def manage_plugins() -> bool:
    if not ask_yes_no("Do you want to install a plugin?"):
        print("Plugin installation skipped.")
        return True

    if not ensure_dependencies({"git": "git"}):
        return False 

    try:
        CUSTOM_PLUGIN_PATH.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        print(f"Failed to create plugin directory {CUSTOM_PLUGIN_PATH}: {error}")
        return False

    while True:
        install_plugin()

        if not ask_yes_no("Do you want to install another plugin?"):
            break

    print("Done isntalling plugins")
    return True

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nSetup interrupted by user.")
        raise SystemExit(130)

