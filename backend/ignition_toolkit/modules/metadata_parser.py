"""
Module metadata parser for extracting information from .modl files
"""

import logging
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ModuleMetadata:
    """Module metadata extracted from .modl file"""

    name: str
    version: str
    id: str
    description: Optional[str] = None
    vendor: Optional[str] = None
    file_path: str = ""


def parse_module_metadata(file_path: str) -> Optional[ModuleMetadata]:
    """
    Parse module metadata from a .modl file

    .modl files are ZIP files containing a module.xml file with metadata

    Args:
        file_path: Path to .modl or .unsigned.modl file

    Returns:
        ModuleMetadata if successful, None if parsing fails
    """
    try:
        path = Path(file_path)

        if not path.exists():
            logger.error(f"Module file not found: {file_path}")
            return None

        if not path.suffix in [".modl", ".mod"]:
            # Handle .unsigned.modl files
            if not file_path.endswith(".unsigned.modl"):
                logger.error(f"Invalid module file extension: {file_path}")
                return None

        # Open the .modl file as a ZIP
        with zipfile.ZipFile(file_path, "r") as zip_file:
            # Find module.xml
            module_xml_path = None
            for name in zip_file.namelist():
                if name.endswith("module.xml"):
                    module_xml_path = name
                    break

            if not module_xml_path:
                logger.error(f"module.xml not found in {file_path}")
                return None

            # Read and parse module.xml
            with zip_file.open(module_xml_path) as xml_file:
                tree = ET.parse(xml_file)
                root = tree.getroot()

                # Extract metadata
                name = root.findtext("name", "").strip()
                version = root.findtext("version", "").strip()
                module_id = root.findtext("id", "").strip()
                description = root.findtext("description", "").strip()
                vendor = root.findtext("vendor", "").strip()

                if not name or not version:
                    logger.error(f"Missing required metadata in {file_path}")
                    return None

                return ModuleMetadata(
                    name=name,
                    version=version,
                    id=module_id,
                    description=description or None,
                    vendor=vendor or None,
                    file_path=str(path.absolute()),
                )

    except zipfile.BadZipFile:
        logger.error(f"Invalid ZIP file: {file_path}")
        return None
    except ET.ParseError as e:
        logger.error(f"Failed to parse module.xml: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error parsing module metadata: {e}")
        return None
