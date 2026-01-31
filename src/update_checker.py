"""
Auto-update checker for Advanced File Mover Pro
- Checks GitHub releases for newer versions
- Downloads and installs updates automatically
- Handles restart after installation
"""

import json
import os
import subprocess
import threading
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Tuple
import logging

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)

# GitHub repository info
GITHUB_OWNER = "u064241"
GITHUB_REPO = "advanced-file-mover"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"


def get_local_version(config_path: str) -> str:
    """Read local version from config.json"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config.get("version", "0.0.0")
    except Exception as e:
        logger.error(f"Error reading local version: {e}")
        return "0.0.0"


def get_latest_release_info() -> Optional[dict]:
    """
    Fetch latest release info from GitHub API
    Returns: {version, tag_name, download_url} or None if failed
    """
    if not requests:
        logger.warning("requests module not available, skipping update check")
        return None

    try:
        url = f"{GITHUB_API_URL}/releases/latest"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        tag_name = data.get("tag_name", "").lstrip("v")  # Remove 'v' prefix
        
        # Look for setup.exe or installer
        download_url = None
        for asset in data.get("assets", []):
            asset_name = asset.get("name", "").lower()
            if "setup.exe" in asset_name or "installer" in asset_name:
                download_url = asset.get("browser_download_url")
                break
        
        if not download_url:
            logger.warning("No installer found in release assets")
            return None
        
        return {
            "version": tag_name,
            "tag_name": data.get("tag_name"),
            "download_url": download_url,
            "release_notes": data.get("body", ""),
            "published_at": data.get("published_at")
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching latest release: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in get_latest_release_info: {e}")
        return None


def compare_versions(local: str, remote: str) -> int:
    """
    Compare two semantic versions
    Returns: 
        -1 if local < remote (update available)
         0 if local == remote (no update needed)
         1 if local > remote (local is newer)
    """
    try:
        local_parts = [int(x) for x in local.split('.')]
        remote_parts = [int(x) for x in remote.split('.')]
        
        # Pad with zeros
        while len(local_parts) < len(remote_parts):
            local_parts.append(0)
        while len(remote_parts) < len(local_parts):
            remote_parts.append(0)
        
        if local_parts < remote_parts:
            return -1
        elif local_parts > remote_parts:
            return 1
        else:
            return 0
    except Exception as e:
        logger.error(f"Error comparing versions: {e}")
        return 0


def download_installer(download_url: str, download_path: str) -> bool:
    """Download installer to temporary location"""
    if not requests:
        return False
    
    try:
        logger.info(f"Downloading installer from {download_url}")
        response = requests.get(download_url, stream=True, timeout=30)
        response.raise_for_status()
        
        with open(download_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        logger.info(f"Installer downloaded to {download_path}")
        return True
    except Exception as e:
        logger.error(f"Error downloading installer: {e}")
        return False


def install_and_restart(installer_path: str, on_close_app=None) -> bool:
    """
    Execute installer and restart application
    Works on Windows with .exe files
    
    Args:
        installer_path: Path to the installer executable
        on_close_app: Callback to close the current application cleanly
    """
    try:
        logger.info(f"Starting installer: {installer_path}")
        
        # Signal the application to close cleanly BEFORE running installer
        if on_close_app:
            logger.info("Requesting application to close...")
            on_close_app()
            # Give app time to close (Tkinter needs time to cleanup)
            # Increased from 1 to 3 seconds to ensure complete termination
            import time
            time.sleep(3)
        
        # Execute installer silently (depends on installer configuration)
        # For Inno Setup: /SILENT /NORESTART /ALLUSERS
        process = subprocess.Popen(
            [installer_path, "/SILENT", "/NORESTART", "/ALLUSERS"],
            shell=False,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
        
        # Wait for installer to complete (max 5 minutes)
        logger.info("Waiting for installer to complete...")
        try:
            process.wait(timeout=300)
            logger.info("Installer completed successfully")
        except subprocess.TimeoutExpired:
            logger.warning("Installer timeout (300s), continuing anyway")
        
        logger.info("Installation complete, exiting application")
        return True
    except Exception as e:
        logger.error(f"Error executing installer: {e}")
        # Fallback: ask user to run installer manually
        try:
            os.startfile(installer_path)
            return True
        except Exception as e2:
            logger.error(f"Error opening installer: {e2}")
            return False


def check_and_update(
    config_path: str,
    on_update_available=None,
    on_download_start=None,
    on_download_complete=None,
    on_close_app=None,
    on_error=None
) -> Tuple[bool, Optional[str]]:
    """
    Main update check and download function
    
    Args:
        config_path: Path to config.json
        on_update_available: Callback when update is found
        on_download_start: Callback when download starts
        on_download_complete: Callback when download completes
        on_close_app: Callback to close application before installing
        on_error: Callback for errors
    
    Returns:
        (success: bool, message: str)
    """
    try:
        local_version = get_local_version(config_path)
        logger.info(f"Local version: {local_version}")
        
        release_info = get_latest_release_info()
        if not release_info:
            return False, "Could not fetch release information"
        
        remote_version = release_info["version"]
        logger.info(f"Remote version: {remote_version}")
        
        cmp_result = compare_versions(local_version, remote_version)
        
        if cmp_result >= 0:
            msg = "No update available" if cmp_result == 0 else "Local version is newer"
            logger.info(msg)
            return False, msg
        
        # Update available
        logger.info(f"Update available: {remote_version}")
        if on_update_available:
            on_update_available(remote_version, release_info.get("release_notes", ""))
        
        # Download installer
        if on_download_start:
            on_download_start()
        
        temp_dir = tempfile.gettempdir()
        installer_name = f"AdvancedFileMover_Setup.exe"
        installer_path = os.path.join(temp_dir, installer_name)
        
        success = download_installer(release_info["download_url"], installer_path)
        
        if on_download_complete:
            on_download_complete(success)
        
        if not success:
            return False, "Failed to download installer"
        
        # Execute installer (with app close callback)
        install_success = install_and_restart(installer_path, on_close_app=on_close_app)
        
        if install_success:
            return True, f"Update to {remote_version} started"
        else:
            return False, f"Could not execute installer at {installer_path}"
    
    except Exception as e:
        error_msg = f"Update check failed: {str(e)}"
        logger.error(error_msg)
        if on_error:
            on_error(error_msg)
        return False, error_msg


def check_for_update_async(
    config_path: str,
    on_update_available=None,
    on_error=None
) -> threading.Thread:
    """
    Run update check in background thread
    
    Returns:
        Thread object (already started)
    """
    def _check():
        check_and_update(config_path, on_update_available=on_update_available, on_error=on_error)
    
    thread = threading.Thread(target=_check, daemon=True)
    thread.start()
    return thread


if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)
    config_path = "config.json"
    success, msg = check_and_update(config_path)
    print(f"Result: {success}, Message: {msg}")
