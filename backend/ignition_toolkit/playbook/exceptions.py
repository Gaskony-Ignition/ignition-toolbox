"""
Playbook execution exceptions
"""


class PlaybookError(Exception):
    """Base exception for playbook errors"""

    pass


class PlaybookLoadError(PlaybookError):
    """Error loading playbook from file"""

    pass


class PlaybookValidationError(PlaybookError):
    """Error validating playbook structure"""

    pass


class PlaybookExecutionError(PlaybookError):
    """Error during playbook execution"""

    pass


class StepExecutionError(PlaybookError):
    """Error executing individual step"""

    def __init__(self, step_id: str, message: str):
        self.step_id = step_id
        super().__init__(f"Step '{step_id}' failed: {message}")


class ParameterResolutionError(PlaybookError):
    """Error resolving parameter value"""

    pass
