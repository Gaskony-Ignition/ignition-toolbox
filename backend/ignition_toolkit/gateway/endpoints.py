"""
Gateway REST API endpoint definitions
"""


class GatewayEndpoints:
    """
    Ignition Gateway REST API endpoints for version 8.3+

    All endpoints are relative to the gateway base URL (e.g., http://localhost:8088)
    """

    # Authentication
    LOGIN = "/system/login"
    LOGOUT = "/system/logout"

    # System information
    STATUS_PING = "/StatusPing"
    GATEWAY_INFO = "/system/gwinfo"
    HEALTH = "/system/health"  # Custom health check endpoint

    # Module management
    MODULES_LIST = "/system/modules"
    MODULE_UPLOAD = "/system/modules/upload"
    MODULE_INSTALL = "/system/modules/install"
    MODULE_DELETE = "/system/modules/delete"

    # Project management
    PROJECTS_LIST = "/data/project-list"
    PROJECT_CREATE = "/data/project"
    PROJECT_GET = "/data/project/{project_name}"
    PROJECT_UPDATE = "/data/project/{project_name}"
    PROJECT_DELETE = "/data/project/{project_name}"
    PROJECT_EXPORT = "/data/project/export/{project_name}"
    PROJECT_IMPORT = "/data/project/import"

    # Tag operations
    TAG_READ = "/data/tags/{tag_path}"
    TAG_WRITE = "/data/tags/{tag_path}/value"
    TAG_CREATE = "/data/tags/{tag_path}"
    TAG_DELETE = "/data/tags/{tag_path}"
    TAG_BROWSE = "/data/tags/browse"

    # System operations
    RESTART = "/system/restart"
    BACKUP_CREATE = "/system/backup"
    BACKUP_RESTORE = "/system/backup/restore"
    BACKUP_LIST = "/system/backups"

    # Designer operations
    DESIGNER_LAUNCH = "/system/launch/designer/{project_name}"

    # Perspective operations
    PERSPECTIVE_SESSION = "/data/perspective/client/{project_name}"
