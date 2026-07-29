#!/usr/bin/env python3
import os
import pwd
import shutil
import subprocess
from pathlib import Path

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
    return 0

# starting here we check for omz 
def oh_my_zsh_installed() -> bool:
    return OMZ_SCRIPT_PATH.is_file()

def ensure_oh_my_zsh() -> bool:
    installer_path = Path("/tmp/oh-my-zsh-install.sh")
    installer_url = "https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh"
    curl_path = shutil.which("curl")
    git_path = shutil.which("git")


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


    if curl_path is None:
        print("Curl is required to install OMZ")
        if not ask_yes_no("Do you want to install Curl?"):
            print("Curl installation skipped.")
            return False
        if not run_command(["sudo", "apt-get", "update"]):
            return False
        if not run_command(["sudo", "apt-get", "install", "-y", "curl"]):
            return False
        
        curl_path = shutil.which("curl")

        if curl_path is None:
            print("Curl was installed, but could not be detected.")
            return False

    if git_path is None:
        print("Git is required to install OMZ")

        if not ask_yes_no("Do you want to install Git?"):
            print("Git installation skipped.")
            return False
        if not run_command(["sudo", "apt-get", "update"]):
            return False
        if not run_command(["sudo", "apt-get", "install", "-y", "git"]):
            return False
        git_path = shutil.which("git")

        if git_path is None:
            print("Git was installed, but could not be detected.")
            return False

    installer_path.unlink(missing_ok=True)

    try:
        if not run_command([curl_path, "-fsSL", installer_url, "-o", str(installer_path)]):
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



if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nSetup interrupted by user.")
        raise SystemExit(130)

