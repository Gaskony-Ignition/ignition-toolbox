"""
Windows desktop automation for Ignition Designer using pywinauto

Handles Designer window detection, interaction, and automation on Windows.
"""

import logging
import time

logger = logging.getLogger(__name__)

try:
    from pywinauto import Application, Desktop
    from pywinauto.findwindows import ElementNotFoundError
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False
    logger.warning("pywinauto not available - Windows Designer automation disabled")


class WindowsDesignerAutomation:
    """
    Windows-specific Designer automation using pywinauto
    """

    def __init__(self):
        if not PYWINAUTO_AVAILABLE:
            raise ImportError("pywinauto is required for Windows Designer automation. Install with: pip install pywinauto")

        self.app: Application | None = None
        self.main_window = None
        self.login_window = None

    def find_designer_window(self, timeout: int = 30) -> bool:
        """
        Find Designer main window

        Args:
            timeout: Maximum time to wait for window (seconds)

        Returns:
            True if window found, False otherwise
        """
        logger.info("Searching for Designer window...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # Try different window title patterns
                title_patterns = [
                    "Ignition Designer",
                    "Designer - ",
                    "Ignition",
                ]

                for pattern in title_patterns:
                    try:
                        # Use Desktop to find existing windows
                        desktop = Desktop(backend="uia")
                        windows = desktop.windows()

                        for win in windows:
                            title = win.window_text()
                            if pattern.lower() in title.lower():
                                logger.info(f"Found Designer window: {title}")
                                self.app = Application(backend="uia").connect(title=title)
                                self.main_window = self.app.window(title=title)
                                return True
                    except ElementNotFoundError:
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
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # Try to find login dialog by title
                desktop = Desktop(backend="uia")
                windows = desktop.windows()

                for win in windows:
                    title = win.window_text().lower()
                    # Common login dialog titles
                    if any(keyword in title for keyword in ["login", "sign in", "authentication", "credentials"]):
                        logger.info(f"Found login dialog: {win.window_text()}")
                        self.login_window = win
                        return True

                time.sleep(0.5)
            except Exception as e:
                logger.debug(f"Login dialog search error: {e}")
                time.sleep(0.5)

        logger.warning(f"Login dialog not found after {timeout}s")
        return False

    def fill_login_credentials(self, username: str, password: str) -> bool:
        """
        Fill Designer login credentials

        Args:
            username: Username
            password: Password

        Returns:
            True if successful, False otherwise
        """
        if not self.login_window:
            logger.error("No login window available")
            return False

        try:
            logger.info(f"Filling login credentials for user: {username}")

            # Try to find username and password fields
            # Method 1: By control type (Edit controls)
            edit_controls = self.login_window.descendants(control_type="Edit")

            if len(edit_controls) >= 2:
                # Typically first edit is username, second is password
                username_field = edit_controls[0]
                password_field = edit_controls[1]

                # Clear and fill fields
                username_field.set_text(username)
                logger.debug("Username filled")

                password_field.set_text(password)
                logger.debug("Password filled")

                # Find and click login button
                buttons = self.login_window.descendants(control_type="Button")
                for button in buttons:
                    button_text = button.window_text().lower()
                    if any(keyword in button_text for keyword in ["login", "sign in", "ok", "connect"]):
                        logger.info(f"Clicking login button: {button.window_text()}")
                        button.click()
                        return True

                logger.warning("Login button not found")
                return False
            else:
                logger.warning(f"Expected 2 edit controls, found {len(edit_controls)}")
                return False

        except Exception as e:
            logger.error(f"Error filling login credentials: {e}")
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
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # Check if login window still exists
                if not self.login_window.exists():
                    logger.info("Login dialog closed - login successful")
                    return True
                time.sleep(0.5)
            except Exception:
                # Window no longer exists
                logger.info("Login dialog closed - login successful")
                return True

        logger.warning(f"Login did not complete after {timeout}s")
        return False

    def find_project_selector(self, timeout: int = 10) -> bool:
        """
        Find project selection dialog

        Args:
            timeout: Maximum time to wait (seconds)

        Returns:
            True if dialog found, False otherwise
        """
        logger.info("Searching for project selector...")
        # Project selector is typically in the main Designer window
        return self.find_designer_window(timeout=timeout)

    def select_project(self, project_name: str, timeout: int = 10) -> bool:
        """
        Select project from project selector

        Args:
            project_name: Name of project to open
            timeout: Maximum time to wait (seconds)

        Returns:
            True if successful, False otherwise
        """
        if not self.main_window:
            logger.error("No Designer window available")
            return False

        try:
            logger.info(f"Looking for project: {project_name}")

            # Look for list or tree controls that might contain projects
            list_controls = self.main_window.descendants(control_type="List")
            tree_controls = self.main_window.descendants(control_type="Tree")

            # Try lists first
            for list_ctrl in list_controls:
                items = list_ctrl.descendants(control_type="ListItem")
                for item in items:
                    if project_name.lower() in item.window_text().lower():
                        logger.info(f"Found project in list: {item.window_text()}")
                        item.click()

                        # Click Open button
                        buttons = self.main_window.descendants(control_type="Button")
                        for button in buttons:
                            if "open" in button.window_text().lower():
                                button.click()
                                logger.info("Clicked Open button")
                                return True
                        return True

            # Try trees
            for tree_ctrl in tree_controls:
                items = tree_ctrl.descendants(control_type="TreeItem")
                for item in items:
                    if project_name.lower() in item.window_text().lower():
                        logger.info(f"Found project in tree: {item.window_text()}")
                        item.click()

                        # Click Open button
                        buttons = self.main_window.descendants(control_type="Button")
                        for button in buttons:
                            if "open" in button.window_text().lower():
                                button.click()
                                logger.info("Clicked Open button")
                                return True
                        return True

            logger.warning(f"Project not found: {project_name}")
            return False

        except Exception as e:
            logger.error(f"Error selecting project: {e}")
            return False

    def close_designer(self) -> bool:
        """
        Close Designer application

        Returns:
            True if successful, False otherwise
        """
        if not self.main_window:
            logger.warning("No Designer window to close")
            return False

        try:
            logger.info("Closing Designer...")
            self.main_window.close()
            logger.info("Designer closed")
            return True
        except Exception as e:
            logger.error(f"Error closing Designer: {e}")
            return False

    def take_screenshot(self, output_path: str) -> bool:
        """
        Take screenshot of Designer window

        Args:
            output_path: Path to save screenshot

        Returns:
            True if successful, False otherwise
        """
        if not self.main_window:
            logger.error("No Designer window available")
            return False

        try:
            logger.info(f"Taking screenshot: {output_path}")
            self.main_window.capture_as_image().save(output_path)
            return True
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return False
