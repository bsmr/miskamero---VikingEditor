import os
import re
import psutil
from pathlib import Path
from typing import Optional

VALHEIM_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "valheim_config.json"
)

def is_valheim_running() -> bool:
    try:
        processes = psutil.process_iter(['pid', 'name', 'exe'])

        for proc in processes:
            try:
                proc_name = proc.info['name'].lower()

                if 'valheim' in proc_name:
                    return True

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess
            ):
                continue

        return False

    except Exception as e:
        print(f"Error checking for Valheim process: {e}")
        return False


def get_valheim_process_info() -> Optional[dict]:
    try:
        processes = psutil.process_iter(
            ['pid', 'name', 'exe', 'cmdline']
        )

        for proc in processes:
            try:
                proc_name = proc.info['name'].lower()

                if 'valheim' in proc_name:
                    return {
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'exe': proc.info['exe'],
                        'cmdline': proc.info['cmdline']
                    }

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess
            ):
                continue

        return None

    except Exception as e:
        print(f"Error getting Valheim process info: {e}")
        return None


def valheim_warning_message() -> str:
    info = get_valheim_process_info()

    if info:
        return (
            f"WARNING: Valheim is currently running!\n\n"
            f"Process Name: {info['name']}\n"
            f"Process ID: {info['pid']}\n"
            f"Executable: {info['exe']}\n\n"
            f"Please close Valheim before using this editor "
            f"to avoid potential conflicts."
        )

    return "Valheim is not currently running."


def is_valid_valheim_installation(path: Path) -> bool:
    """Check whether a directory contains a Valheim installation."""

    if not path.is_dir():
        return False

    bundles_dir = (
        path
        / "valheim_Data"
        / "StreamingAssets"
        / "SoftRef"
        / "Bundles"
    )

    return bundles_dir.is_dir()


def get_steam_installations() -> list[Path]:
    """Find Steam installation/library locations."""

    installations = []

    program_files_paths = [
        os.environ.get("PROGRAMFILES(X86)"),
        os.environ.get("PROGRAMFILES"),
        os.environ.get("LOCALAPPDATA"),
    ]

    for program_files in program_files_paths:
        if not program_files:
            continue

        steam_path = Path(program_files) / "Steam"

        if steam_path.is_dir():
            installations.append(steam_path)

    return installations


def parse_steam_library_paths(steam_path: Path) -> list[Path]:
    """Read Steam's libraryfolders.vdf and return library paths."""

    library_file = (
        steam_path
        / "steamapps"
        / "libraryfolders.vdf"
    )

    if not library_file.is_file():
        return []

    try:
        content = library_file.read_text(
            encoding="utf-8",
            errors="ignore"
        )
    except OSError:
        return []

    paths = []

    # Steam's VDF contains entries such as:
    #
    # "path"    "C:\\Program Files (x86)\\Steam"
    #
    # Match the path regardless of which library entry contains it.
    matches = re.findall(
        r'"path"\s*"([^"]+)"',
        content,
        re.IGNORECASE
    )

    for match in matches:
        library_path = Path(match.replace("\\\\", "\\"))

        if library_path.is_dir():
            paths.append(library_path)

    return paths


def find_valheim_installation() -> Optional[Path]:
    """
    Try to find the Valheim installation through Steam.

    Returns:
        Path: Valheim installation directory if found.
        None: If Valheim cannot be found.
    """

    checked_libraries = []

    for steam_path in get_steam_installations():

        libraries = [steam_path]

        libraries.extend(
            parse_steam_library_paths(steam_path)
        )

        for library in libraries:

            if library in checked_libraries:
                continue

            checked_libraries.append(library)

            valheim_path = (
                library
                / "steamapps"
                / "common"
                / "Valheim"
            )

            if is_valid_valheim_installation(valheim_path):
                return valheim_path

    return None

def load_saved_valheim_path() -> Optional[Path]:
    """Load the previously saved Valheim installation path."""

    if not VALHEIM_CONFIG_PATH.is_file():
        return None

    try:
        import json

        with VALHEIM_CONFIG_PATH.open(
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        path = data.get("valheim_dir")

        if not path:
            return None

        return Path(path)

    except (OSError, ValueError, TypeError):
        return None


def save_valheim_path(valheim_dir):
    """Save the Valheim installation path for future use."""

    import json

    VALHEIM_CONFIG_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with VALHEIM_CONFIG_PATH.open(
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            {
                "valheim_dir": str(valheim_dir)
            },
            file,
            indent=2
        )