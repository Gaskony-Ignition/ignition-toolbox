"""
Step executors using Strategy Pattern

Each executor handles a specific domain of step types (gateway, browser, designer, etc.)
This allows for better separation of concerns and easier testing.
"""

from ignition_toolkit.playbook.executors.base import StepHandler
from ignition_toolkit.playbook.executors.gateway_executor import (
    GatewayGetHealthHandler,
    GatewayGetInfoHandler,
    GatewayGetProjectHandler,
    GatewayListModulesHandler,
    GatewayListProjectsHandler,
    GatewayLoginHandler,
    GatewayLogoutHandler,
    GatewayPingHandler,
    GatewayRestartHandler,
    GatewayUploadModuleHandler,
    GatewayWaitModuleHandler,
    GatewayWaitReadyHandler,
)
from ignition_toolkit.playbook.executors.browser_executor import (
    BrowserClickHandler,
    BrowserFillHandler,
    BrowserFileUploadHandler,
    BrowserNavigateHandler,
    BrowserScreenshotHandler,
    BrowserVerifyHandler,
    BrowserVerifyTextHandler,
    BrowserVerifyAttributeHandler,
    BrowserVerifyStateHandler,
    BrowserWaitHandler,
)
from ignition_toolkit.playbook.executors.designer_executor import (
    DesignerCloseHandler,
    DesignerLaunchHandler,
    DesignerLaunchShortcutHandler,
    DesignerLoginHandler,
    DesignerOpenProjectHandler,
    DesignerScreenshotHandler,
    DesignerWaitHandler,
)
from ignition_toolkit.playbook.executors.playbook_executor import PlaybookRunHandler
from ignition_toolkit.playbook.executors.utility_executor import (
    UtilityLogHandler,
    UtilityPythonHandler,
    UtilitySetVariableHandler,
    UtilitySleepHandler,
)
from ignition_toolkit.playbook.executors.perspective_executor import (
    PerspectiveDiscoverPageHandler,
    PerspectiveExtractMetadataHandler,
    PerspectiveExecuteTestManifestHandler,
    PerspectiveVerifyNavigationHandler,
    PerspectiveVerifyDockHandler,
)
from ignition_toolkit.playbook.executors.fat_executor import (
    FATGenerateReportHandler,
    FATExportReportHandler,
)

__all__ = [
    "StepHandler",
    # Gateway
    "GatewayLoginHandler",
    "GatewayLogoutHandler",
    "GatewayPingHandler",
    "GatewayGetInfoHandler",
    "GatewayGetHealthHandler",
    "GatewayListModulesHandler",
    "GatewayUploadModuleHandler",
    "GatewayWaitModuleHandler",
    "GatewayListProjectsHandler",
    "GatewayGetProjectHandler",
    "GatewayRestartHandler",
    "GatewayWaitReadyHandler",
    # Browser
    "BrowserNavigateHandler",
    "BrowserClickHandler",
    "BrowserFillHandler",
    "BrowserFileUploadHandler",
    "BrowserScreenshotHandler",
    "BrowserWaitHandler",
    "BrowserVerifyHandler",
    "BrowserVerifyTextHandler",
    "BrowserVerifyAttributeHandler",
    "BrowserVerifyStateHandler",
    # Designer
    "DesignerLaunchHandler",
    "DesignerLaunchShortcutHandler",
    "DesignerLoginHandler",
    "DesignerOpenProjectHandler",
    "DesignerCloseHandler",
    "DesignerScreenshotHandler",
    "DesignerWaitHandler",
    # Playbook
    "PlaybookRunHandler",
    # Utility
    "UtilitySleepHandler",
    "UtilityLogHandler",
    "UtilitySetVariableHandler",
    "UtilityPythonHandler",
    # Perspective FAT
    "PerspectiveDiscoverPageHandler",
    "PerspectiveExtractMetadataHandler",
    "PerspectiveExecuteTestManifestHandler",
    "PerspectiveVerifyNavigationHandler",
    "PerspectiveVerifyDockHandler",
    # FAT Reporting
    "FATGenerateReportHandler",
    "FATExportReportHandler",
]
