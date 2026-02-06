"""
Step type metadata API endpoint

Returns metadata for all available step types including:
- Type name (e.g., 'gateway.login')
- Domain (gateway, browser, designer, perspective, utility, playbook, fat)
- Description of what the step does
- Parameter definitions with type, required, default, and description
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/playbooks", tags=["playbooks"])


class StepParameter(BaseModel):
    """Parameter definition for a step type"""
    name: str
    type: str  # string, integer, float, boolean, credential, file, list, dict, selector
    required: bool = True
    default: str | int | float | bool | None = None
    description: str = ""
    options: list[str] | None = None  # For enum-like parameters


class StepTypeInfo(BaseModel):
    """Metadata for a step type"""
    type: str
    domain: str
    description: str
    parameters: list[StepParameter]


class StepTypesResponse(BaseModel):
    """Response containing all step types"""
    step_types: list[StepTypeInfo]
    domains: list[str]


# Define step type metadata
STEP_TYPE_METADATA: list[StepTypeInfo] = [
    # Gateway Operations
    StepTypeInfo(
        type="gateway.login",
        domain="gateway",
        description="Login to Ignition Gateway with username and password",
        parameters=[
            StepParameter(name="credential", type="credential", required=True,
                         description="Credential containing gateway login information"),
        ]
    ),
    StepTypeInfo(
        type="gateway.logout",
        domain="gateway",
        description="Logout from Ignition Gateway",
        parameters=[]
    ),
    StepTypeInfo(
        type="gateway.ping",
        domain="gateway",
        description="Ping the Gateway to verify connectivity",
        parameters=[]
    ),
    StepTypeInfo(
        type="gateway.get_info",
        domain="gateway",
        description="Get Gateway system information (version, edition, etc.)",
        parameters=[]
    ),
    StepTypeInfo(
        type="gateway.get_health",
        domain="gateway",
        description="Get Gateway health status",
        parameters=[]
    ),
    StepTypeInfo(
        type="gateway.list_modules",
        domain="gateway",
        description="List all installed modules on the Gateway",
        parameters=[]
    ),
    StepTypeInfo(
        type="gateway.upload_module",
        domain="gateway",
        description="Upload and install a module (.modl file) to the Gateway",
        parameters=[
            StepParameter(name="file", type="file", required=True,
                         description="Path to the .modl file to upload"),
        ]
    ),
    StepTypeInfo(
        type="gateway.wait_for_module_installation",
        domain="gateway",
        description="Wait for a module to finish installing",
        parameters=[
            StepParameter(name="module_name", type="string", required=True,
                         description="Name of the module to wait for"),
            StepParameter(name="timeout", type="integer", required=False, default=300,
                         description="Maximum time to wait in seconds"),
        ]
    ),
    StepTypeInfo(
        type="gateway.list_projects",
        domain="gateway",
        description="List all projects on the Gateway",
        parameters=[]
    ),
    StepTypeInfo(
        type="gateway.get_project",
        domain="gateway",
        description="Get details for a specific project",
        parameters=[
            StepParameter(name="project_name", type="string", required=True,
                         description="Name of the project to retrieve"),
        ]
    ),
    StepTypeInfo(
        type="gateway.restart",
        domain="gateway",
        description="Restart the Ignition Gateway",
        parameters=[
            StepParameter(name="wait_for_ready", type="boolean", required=False, default=False,
                         description="Wait for Gateway to be ready after restart"),
            StepParameter(name="timeout", type="integer", required=False, default=120,
                         description="Maximum time to wait in seconds"),
        ]
    ),
    StepTypeInfo(
        type="gateway.wait_for_ready",
        domain="gateway",
        description="Wait for Gateway to be ready and accepting connections",
        parameters=[
            StepParameter(name="timeout", type="integer", required=False, default=120,
                         description="Maximum time to wait in seconds"),
        ]
    ),

    # Browser Operations
    StepTypeInfo(
        type="browser.navigate",
        domain="browser",
        description="Navigate the browser to a URL",
        parameters=[
            StepParameter(name="url", type="string", required=True,
                         description="URL to navigate to"),
            StepParameter(name="wait_until", type="string", required=False, default="load",
                         description="When to consider navigation complete",
                         options=["load", "domcontentloaded", "networkidle"]),
        ]
    ),
    StepTypeInfo(
        type="browser.click",
        domain="browser",
        description="Click on an element in the page",
        parameters=[
            StepParameter(name="selector", type="selector", required=True,
                         description="CSS selector for the element to click"),
            StepParameter(name="timeout", type="integer", required=False, default=30000,
                         description="Maximum time to wait for element in milliseconds"),
            StepParameter(name="force", type="boolean", required=False, default=False,
                         description="Force click even if element is not visible"),
        ]
    ),
    StepTypeInfo(
        type="browser.fill",
        domain="browser",
        description="Fill a form field with text",
        parameters=[
            StepParameter(name="selector", type="selector", required=True,
                         description="CSS selector for the input element"),
            StepParameter(name="value", type="string", required=True,
                         description="Text value to fill"),
            StepParameter(name="timeout", type="integer", required=False, default=30000,
                         description="Maximum time to wait for element in milliseconds"),
        ]
    ),
    StepTypeInfo(
        type="browser.keyboard",
        domain="browser",
        description="Send keyboard input to the page",
        parameters=[
            StepParameter(name="key", type="string", required=True,
                         description="Key or key combination to press (e.g., 'Enter', 'Control+A')"),
        ]
    ),
    StepTypeInfo(
        type="browser.file_upload",
        domain="browser",
        description="Upload a file through a file input element",
        parameters=[
            StepParameter(name="selector", type="selector", required=True,
                         description="CSS selector for the file input element"),
            StepParameter(name="file_path", type="file", required=True,
                         description="Path to the file to upload"),
            StepParameter(name="timeout", type="integer", required=False, default=30000,
                         description="Maximum time to wait for element in milliseconds"),
        ]
    ),
    StepTypeInfo(
        type="browser.screenshot",
        domain="browser",
        description="Capture a screenshot of the current page",
        parameters=[
            StepParameter(name="name", type="string", required=False,
                         description="Name for the screenshot file"),
            StepParameter(name="full_page", type="boolean", required=False, default=False,
                         description="Capture full scrollable page"),
        ]
    ),
    StepTypeInfo(
        type="browser.wait",
        domain="browser",
        description="Wait for an element to appear on the page",
        parameters=[
            StepParameter(name="selector", type="selector", required=True,
                         description="CSS selector for the element to wait for"),
            StepParameter(name="timeout", type="integer", required=False, default=30000,
                         description="Maximum time to wait in milliseconds"),
        ]
    ),
    StepTypeInfo(
        type="browser.verify",
        domain="browser",
        description="Verify that an element exists or does not exist",
        parameters=[
            StepParameter(name="selector", type="selector", required=True,
                         description="CSS selector for the element to verify"),
            StepParameter(name="exists", type="boolean", required=False, default=True,
                         description="True to verify element exists, False to verify it doesn't"),
            StepParameter(name="timeout", type="integer", required=False, default=5000,
                         description="Maximum time to wait in milliseconds"),
        ]
    ),
    StepTypeInfo(
        type="browser.verify_text",
        domain="browser",
        description="Verify text content of an element",
        parameters=[
            StepParameter(name="selector", type="selector", required=True,
                         description="CSS selector for the element"),
            StepParameter(name="text", type="string", required=True,
                         description="Expected text content"),
            StepParameter(name="match", type="string", required=False, default="exact",
                         description="Match type: exact, contains, or regex",
                         options=["exact", "contains", "regex"]),
            StepParameter(name="timeout", type="integer", required=False, default=5000,
                         description="Maximum time to wait in milliseconds"),
        ]
    ),
    StepTypeInfo(
        type="browser.verify_attribute",
        domain="browser",
        description="Verify an attribute value of an element",
        parameters=[
            StepParameter(name="selector", type="selector", required=True,
                         description="CSS selector for the element"),
            StepParameter(name="attribute", type="string", required=True,
                         description="Name of the attribute to check"),
            StepParameter(name="value", type="string", required=True,
                         description="Expected attribute value"),
            StepParameter(name="timeout", type="integer", required=False, default=5000,
                         description="Maximum time to wait in milliseconds"),
        ]
    ),
    StepTypeInfo(
        type="browser.verify_state",
        domain="browser",
        description="Verify the state of an element (visible, hidden, enabled, disabled)",
        parameters=[
            StepParameter(name="selector", type="selector", required=True,
                         description="CSS selector for the element"),
            StepParameter(name="state", type="string", required=True,
                         description="Expected state of the element",
                         options=["visible", "hidden", "enabled", "disabled"]),
            StepParameter(name="timeout", type="integer", required=False, default=5000,
                         description="Maximum time to wait in milliseconds"),
        ]
    ),

    # Designer Operations
    StepTypeInfo(
        type="designer.launch",
        domain="designer",
        description="Launch the Ignition Designer from a launcher file",
        parameters=[
            StepParameter(name="launcher_file", type="file", required=True,
                         description="Path to the Designer launcher file (.jnlp or .exe)"),
        ]
    ),
    StepTypeInfo(
        type="designer.launch_shortcut",
        domain="designer",
        description="Launch Designer via Windows shortcut with automatic login",
        parameters=[
            StepParameter(name="designer_shortcut", type="string", required=True,
                         description="Name or path of the Designer shortcut"),
            StepParameter(name="project_name", type="string", required=True,
                         description="Name of the project to open"),
            StepParameter(name="gateway_credential", type="credential", required=False,
                         description="Credential for Gateway login"),
            StepParameter(name="username", type="string", required=False,
                         description="Username for Gateway login (if not using credential)"),
            StepParameter(name="password", type="string", required=False,
                         description="Password for Gateway login (if not using credential)"),
            StepParameter(name="timeout", type="integer", required=False, default=60,
                         description="Maximum time to wait for Designer launch in seconds"),
        ]
    ),
    StepTypeInfo(
        type="designer.login",
        domain="designer",
        description="Login to the Designer with username and password",
        parameters=[
            StepParameter(name="username", type="string", required=True,
                         description="Username for Designer login"),
            StepParameter(name="password", type="string", required=True,
                         description="Password for Designer login"),
            StepParameter(name="timeout", type="integer", required=False, default=30,
                         description="Maximum time to wait for login in seconds"),
        ]
    ),
    StepTypeInfo(
        type="designer.open_project",
        domain="designer",
        description="Open a project in the Designer",
        parameters=[
            StepParameter(name="project_name", type="string", required=False,
                         description="Name of the project to open (leave empty for manual selection)"),
            StepParameter(name="timeout", type="integer", required=False, default=30,
                         description="Maximum time to wait in seconds"),
        ]
    ),
    StepTypeInfo(
        type="designer.close",
        domain="designer",
        description="Close the Designer application",
        parameters=[]
    ),
    StepTypeInfo(
        type="designer.screenshot",
        domain="designer",
        description="Capture a screenshot of the Designer window",
        parameters=[
            StepParameter(name="name", type="string", required=False,
                         description="Name for the screenshot file"),
        ]
    ),
    StepTypeInfo(
        type="designer.wait",
        domain="designer",
        description="Wait for the Designer window to appear",
        parameters=[
            StepParameter(name="timeout", type="integer", required=False, default=30,
                         description="Maximum time to wait in seconds"),
        ]
    ),

    # Utility Operations
    StepTypeInfo(
        type="utility.sleep",
        domain="utility",
        description="Pause execution for a specified duration",
        parameters=[
            StepParameter(name="seconds", type="float", required=True,
                         description="Number of seconds to sleep"),
        ]
    ),
    StepTypeInfo(
        type="utility.log",
        domain="utility",
        description="Log a message during playbook execution",
        parameters=[
            StepParameter(name="message", type="string", required=True,
                         description="Message to log"),
            StepParameter(name="level", type="string", required=False, default="info",
                         description="Log level",
                         options=["debug", "info", "warning", "error"]),
        ]
    ),
    StepTypeInfo(
        type="utility.set_variable",
        domain="utility",
        description="Set a variable for use in subsequent steps",
        parameters=[
            StepParameter(name="name", type="string", required=True,
                         description="Name of the variable"),
            StepParameter(name="value", type="string", required=True,
                         description="Value to assign to the variable"),
        ]
    ),
    StepTypeInfo(
        type="utility.python",
        domain="utility",
        description="Execute a Python script (use with caution)",
        parameters=[
            StepParameter(name="script", type="string", required=True,
                         description="Python code to execute"),
        ]
    ),

    # Playbook Operations
    StepTypeInfo(
        type="playbook.run",
        domain="playbook",
        description="Execute another playbook as a nested step",
        parameters=[
            StepParameter(name="playbook_path", type="string", required=True,
                         description="Path to the playbook to execute"),
            StepParameter(name="parameters", type="dict", required=False,
                         description="Parameters to pass to the nested playbook"),
        ]
    ),

    # Perspective FAT Operations
    StepTypeInfo(
        type="perspective.discover_page",
        domain="perspective",
        description="Discover interactive components on a Perspective page",
        parameters=[
            StepParameter(name="selector", type="selector", required=False, default="body",
                         description="Root selector to search within"),
            StepParameter(name="types", type="list", required=False,
                         description="List of component types to discover"),
            StepParameter(name="exclude_selectors", type="list", required=False,
                         description="Selectors to exclude from discovery"),
        ]
    ),
    StepTypeInfo(
        type="perspective.extract_component_metadata",
        domain="perspective",
        description="Extract and enrich metadata for discovered components",
        parameters=[
            StepParameter(name="components", type="list", required=True,
                         description="List of components from discover_page step"),
        ]
    ),
    StepTypeInfo(
        type="perspective.execute_test_manifest",
        domain="perspective",
        description="Execute a test manifest against Perspective components",
        parameters=[
            StepParameter(name="manifest", type="list", required=True,
                         description="List of test definitions to execute"),
            StepParameter(name="capture_screenshots", type="boolean", required=False, default=True,
                         description="Capture screenshots during testing"),
            StepParameter(name="on_failure", type="string", required=False, default="continue",
                         description="Action on test failure",
                         options=["continue", "abort"]),
            StepParameter(name="return_to_baseline", type="boolean", required=False, default=True,
                         description="Return to baseline URL after each test"),
            StepParameter(name="baseline_url", type="string", required=False,
                         description="URL to return to after each test"),
        ]
    ),
    StepTypeInfo(
        type="perspective.verify_navigation",
        domain="perspective",
        description="Verify that navigation occurred to expected URL/title",
        parameters=[
            StepParameter(name="expected_url_pattern", type="string", required=False,
                         description="Expected URL pattern to match"),
            StepParameter(name="expected_title_pattern", type="string", required=False,
                         description="Expected page title pattern to match"),
            StepParameter(name="timeout", type="integer", required=False, default=5000,
                         description="Maximum time to wait in milliseconds"),
        ]
    ),
    StepTypeInfo(
        type="perspective.verify_dock_opened",
        domain="perspective",
        description="Verify that a dock panel has opened",
        parameters=[
            StepParameter(name="dock_selector", type="selector", required=True,
                         description="CSS selector for the dock element"),
            StepParameter(name="timeout", type="integer", required=False, default=3000,
                         description="Maximum time to wait in milliseconds"),
        ]
    ),

    # FAT Reporting Operations
    StepTypeInfo(
        type="fat.generate_report",
        domain="fat",
        description="Generate a Factory Acceptance Test report",
        parameters=[
            StepParameter(name="test_results", type="list", required=True,
                         description="List of test results to include in report"),
            StepParameter(name="title", type="string", required=False, default="FAT Report",
                         description="Report title"),
            StepParameter(name="include_screenshots", type="boolean", required=False, default=True,
                         description="Include screenshots in the report"),
        ]
    ),
    StepTypeInfo(
        type="fat.export_report",
        domain="fat",
        description="Export a FAT report to file",
        parameters=[
            StepParameter(name="report", type="dict", required=True,
                         description="Report data from generate_report step"),
            StepParameter(name="output_path", type="string", required=True,
                         description="Path to save the report"),
            StepParameter(name="format", type="string", required=False, default="html",
                         description="Output format",
                         options=["html", "pdf", "json"]),
        ]
    ),

    # AI Verification Operations
    StepTypeInfo(
        type="perspective.verify_with_ai",
        domain="perspective",
        description="Use AI vision to verify UI elements in a screenshot",
        parameters=[
            StepParameter(name="prompt", type="string", required=True,
                         description="Verification prompt describing what to check (e.g., 'Verify the login form is visible with username and password fields')"),
            StepParameter(name="ai_api_key", type="credential", required=True,
                         description="Anthropic API key for Claude Vision"),
            StepParameter(name="selector", type="selector", required=False,
                         description="CSS selector to screenshot specific element (optional, defaults to full page)"),
            StepParameter(name="confidence_threshold", type="float", required=False, default=0.8,
                         description="Minimum confidence (0.0-1.0) required to pass verification"),
            StepParameter(name="ai_model", type="string", required=False, default="claude-sonnet-4-20250514",
                         description="Claude model to use for verification",
                         options=["claude-sonnet-4-20250514", "claude-opus-4-20250514"]),
        ]
    ),
]


@router.get("/step-types", response_model=StepTypesResponse)
async def get_step_types():
    """
    Get metadata for all available step types.

    Returns step type definitions including:
    - Type identifier (e.g., 'gateway.login')
    - Domain classification (gateway, browser, designer, etc.)
    - Human-readable description
    - Parameter definitions with types, defaults, and descriptions
    """
    # Get unique domains
    domains = sorted(set(step.domain for step in STEP_TYPE_METADATA))

    return StepTypesResponse(
        step_types=STEP_TYPE_METADATA,
        domains=domains
    )
