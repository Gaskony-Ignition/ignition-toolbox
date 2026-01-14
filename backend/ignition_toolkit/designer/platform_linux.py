"""
Linux desktop automation for Ignition Designer using python-xlib and pyatspi

Handles Designer window detection, interaction, and automation on Linux.
"""

import logging
import os
import subprocess
import time
from typing import Any

logger = logging.getLogger(__name__)

# Try to import X11 libraries
try:
    from Xlib import X, display, error
    from Xlib.protocol import event
    XLIB_AVAILABLE = True
except ImportError:
    XLIB_AVAILABLE = False
    logger.warning("python-xlib not available - Linux Designer automation limited")

# Try to import AT-SPI (Assistive Technology Service Provider Interface)
try:
    import pyatspi
    PYATSPI_AVAILABLE = True
except ImportError:
    PYATSPI_AVAILABLE = False
    logger.warning("pyatspi not available - Some Linux Designer automation features limited")


class LinuxDesignerAutomation:
    """
    Linux-specific Designer automation using X11 and AT-SPI
    """

    def __init__(self):
        self.display = None
        self.designer_window = None
        self.window_id = None

        # Initialize X display if available
        if XLIB_AVAILABLE:
            try:
                self.display = display.Display()
                logger.info("X11 display connection established")
            except:
                logger.warning("Could not connect to X display")
                self.display = None

    def find_designer_window(self, timeout: int = 30) -> bool:
        """
        Find Designer main window using X11

        Args:
            timeout: Maximum time to wait for window (seconds)

        Returns:
            True if window found, False otherwise
        """
        if not XLIB_AVAILABLE or not self.display:
            logger.error("X11 not available for window detection")
            return False

        logger.info("Searching for Designer window via X11...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # Get root window
                root = self.display.screen().root

                # Query all windows
                children = root.query_tree().children
                for window in children:
                    try:
                        # Get window name
                        window_name = window.get_wm_name()
                        window_class = window.get_wm_class()

                        # Check if this is Designer
                        if window_name and any(
                            keyword in window_name.lower()
                            for keyword in ["ignition", "designer"]
                        ):
                            logger.info(f"Found Designer window: {window_name}")
                            self.designer_window = window
                            self.window_id = window.id
                            return True

                        # Also check WM_CLASS
                        if window_class:
                            class_str = " ".join(window_class).lower()
                            if any(keyword in class_str for keyword in ["ignition", "designer"]):
                                logger.info(f"Found Designer window by class: {window_class}")
                                self.designer_window = window
                                self.window_id = window.id
                                return True

                    except:
                        continue

                time.sleep(1)
            except Exception as e:
                logger.debug(f"Window search error: {e}")
                time.sleep(1)

        logger.warning(f"Designer window not found after {timeout}s")
        return False

    def find_login_dialog(self, timeout: int = 10) -> bool:
        """
        Find Designer login dialog

        Args:
            timeout: Maximum time to wait for dialog (seconds)

        Returns:
            True if dialog found, False otherwise
        """
        logger.info("Searching for Designer login dialog...")

        # For Linux, login dialog detection is more complex
        # We'll rely on AT-SPI if available, otherwise use X11 window enumeration

        if PYATSPI_AVAILABLE:
            return self._find_login_dialog_atspi(timeout)
        elif XLIB_AVAILABLE:
            return self._find_login_dialog_x11(timeout)
        else:
            logger.error("No automation library available for login dialog detection")
            return False

    def _find_login_dialog_x11(self, timeout: int) -> bool:
        """Find login dialog using X11"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                root = self.display.screen().root
                children = root.query_tree().children

                for window in children:
                    try:
                        window_name = window.get_wm_name()
                        if window_name and any(
                            keyword in window_name.lower()
                            for keyword in ["login", "sign in", "authentication"]
                        ):
                            logger.info(f"Found login dialog: {window_name}")
                            self.designer_window = window  # Treat as active window
                            return True
                    except:
                        continue

                time.sleep(0.5)
            except Exception as e:
                logger.debug(f"Login dialog search error: {e}")
                time.sleep(0.5)

        logger.warning(f"Login dialog not found after {timeout}s")
        return False

    def _find_login_dialog_atspi(self, timeout: int) -> bool:
        """Find login dialog using AT-SPI"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                desktop = pyatspi.Registry.getDesktop(0)
                for app in desktop:
                    for window in app:
                        window_name = window.name.lower()
                        if any(keyword in window_name for keyword in ["login", "sign in"]):
                            logger.info(f"Found login dialog via AT-SPI: {window.name}")
                            return True
                time.sleep(0.5)
            except Exception as e:
                logger.debug(f"AT-SPI dialog search error: {e}")
                time.sleep(0.5)

        return False

    def fill_login_credentials(self, username: str, password: str) -> bool:
        """
        Fill Designer login credentials

        Uses xdotool for keyboard input simulation.

        Args:
            username: Username
            password: Password

        Returns:
            True if successful, False otherwise
        """
        logger.info("Filling login credentials...")

        try:
            # Use xdotool to type credentials
            # This is a simple but effective approach for Linux

            # Focus the window first
            if self.window_id:
                subprocess.run(["xdotool", "windowactivate", str(self.window_id)], check=True)
                time.sleep(0.5)

            # Type username (assumes focus is on username field)
            subprocess.run(["xdotool", "type", "--clearmodifiers", username], check=True)
            logger.debug("Username typed")

            # Press Tab to move to password field
            subprocess.run(["xdotool", "key", "Tab"], check=True)
            time.sleep(0.2)

            # Type password
            subprocess.run(["xdotool", "type", "--clearmodifiers", password], check=True)
            logger.debug("Password typed")

            # Press Enter to submit
            subprocess.run(["xdotool", "key", "Return"], check=True)
            logger.info("Login submitted")

            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"xdotool command failed: {e}")
            return False
        except FileNotFoundError:
            logger.error("xdotool not found. Install with: sudo apt install xdotool")
            return False
        except Exception as e:
            logger.error(f"Error filling credentials: {e}")
            return False

    def wait_for_login_completion(self, timeout: int = 30) -> bool:
        """
        Wait for login dialog to close

        Args:
            timeout: Maximum time to wait (seconds)

        Returns:
            True if login successful, False otherwise
        """
        logger.info("Waiting for login to complete...")
        # For Linux, we'll check if the Designer main window becomes visible
        time.sleep(2)  # Give it a moment

        # Try to find the main Designer window (not login dialog)
        return self.find_designer_window(timeout=timeout)

    def find_project_selector(self, timeout: int = 10) -> bool:
        """
        Find project selection dialog

        Args:
            timeout: Maximum time to wait (seconds)

        Returns:
            True if dialog found, False otherwise
        """
        logger.info("Waiting for project selector...")
        # After login, Designer should show project selector
        time.sleep(1)
        return self.find_designer_window(timeout=timeout)

    def select_project(self, project_name: str, timeout: int = 10) -> bool:
        """
        Select project from project selector

        Uses xdotool to type project name and enter.

        Args:
            project_name: Name of project to open
            timeout: Maximum time to wait (seconds)

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Selecting project: {project_name}")

        try:
            # Focus Designer window
            if self.window_id:
                subprocess.run(["xdotool", "windowactivate", str(self.window_id)], check=True)
                time.sleep(0.5)

            # Type project name (assumes there's a search/filter field)
            subprocess.run(["xdotool", "type", "--clearmodifiers", project_name], check=True)
            time.sleep(0.5)

            # Press Enter to open
            subprocess.run(["xdotool", "key", "Return"], check=True)
            logger.info("Project selection submitted")

            return True

        except Exception as e:
            logger.error(f"Error selecting project: {e}")
            return False

    def close_designer(self) -> bool:
        """
        Close Designer application

        Returns:
            True if successful, False otherwise
        """
        if not self.designer_window:
            logger.warning("No Designer window to close")
            return False

        try:
            logger.info("Closing Designer...")

            # Send close event
            if self.display:
                # Create ClientMessage event for WM_DELETE_WINDOW
                wm_protocols = self.display.intern_atom("WM_PROTOCOLS")
                wm_delete = self.display.intern_atom("WM_DELETE_WINDOW")

                ev = event.ClientMessage(
                    window=self.designer_window,
                    client_type=wm_protocols,
                    data=(32, [wm_delete, X.CurrentTime, 0, 0, 0])
                )

                self.designer_window.send_event(ev)
                self.display.flush()

            logger.info("Close event sent")
            return True

        except Exception as e:
            logger.error(f"Error closing Designer: {e}")
            return False

    def take_screenshot(self, output_path: str) -> bool:
        """
        Take screenshot of Designer window

        Uses ImageMagick's import command.

        Args:
            output_path: Path to save screenshot

        Returns:
            True if successful, False otherwise
        """
        if not self.window_id:
            logger.error("No Designer window available")
            return False

        try:
            logger.info(f"Taking screenshot: {output_path}")

            # Use import command (ImageMagick)
            subprocess.run(
                ["import", "-window", str(self.window_id), output_path],
                check=True,
                timeout=5
            )

            logger.info("Screenshot captured")
            return True

        except FileNotFoundError:
            logger.error("ImageMagick not found. Install with: sudo apt install imagemagick")
            return False
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return False

    def __del__(self):
        """Cleanup X display connection"""
        if self.display:
            self.display.close()
