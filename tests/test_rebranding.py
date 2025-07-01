import pytest
from pathlib import Path
from src.config import settings # Import the application settings

# Define strings that should NOT be present after rebranding
OLD_BRAND_STRINGS = [
    "OriginalProjectName",       # Generic placeholder from user's rebrand script
    "original_author",           # Generic placeholder
    "Sovereign Anomaly Detection Agent", # Old project name often used
    "Sovereign Systems",         # Old author name in API info
    # Add more specific old strings if they were prominent and should be gone
]

# Define strings that SHOULD BE present after rebranding
NEW_BRAND_STRINGS_IN_README = [
    "Iniity Sovereign AI Agent",
    "Iniity Inc.",
    "iniity.com",
    "IniitySovereignAgent.git" # Part of the new repo URL
]

NEW_APP_NAME_IN_CONFIG = "Iniity Sovereign AI Agent"
NEW_COPYRIGHT_IN_CONFIG = "Iniity Inc."

def test_readme_rebranding():
    """
    Checks if old branding is removed and new branding is present in README.md.
    This test is most effective AFTER rebranding scripts/manual changes are applied.
    """
    readme_path = Path("README.md")
    assert readme_path.exists(), "README.md should exist"

    readme_content = readme_path.read_text(encoding="utf-8")

    for old_string in OLD_BRAND_STRINGS:
        assert old_string not in readme_content, \
            f"Old branding string '{old_string}' should not be in README.md"

    for new_string in NEW_BRAND_STRINGS_IN_README:
        assert new_string in readme_content, \
            f"New branding string '{new_string}' should be in README.md"

def test_config_rebranding():
    """
    Checks if branding-related settings in src.config.settings are updated.
    This test relies on the current values in the imported settings object.
    """
    assert settings.APP_NAME == NEW_APP_NAME_IN_CONFIG, \
        f"settings.APP_NAME should be '{NEW_APP_NAME_IN_CONFIG}'"
    assert settings.COPYRIGHT_HOLDER == NEW_COPYRIGHT_IN_CONFIG, \
        f"settings.COPYRIGHT_HOLDER should be '{NEW_COPYRIGHT_IN_CONFIG}'"

def test_dockerfile_rebranding():
    """
    Checks for new branding in Dockerfile labels.
    This test is most effective AFTER Dockerfile is updated.
    """
    dockerfile_path = Path("Dockerfile")
    assert dockerfile_path.exists(), "Dockerfile should exist"

    dockerfile_content = dockerfile_path.read_text(encoding="utf-8")

    assert 'LABEL maintainer="Your Engineering Team <dev@yourcompany.com>"' not in dockerfile_content
    assert 'LABEL description="Proprietary AI Agent by YourCompany"' not in dockerfile_content

    assert 'LABEL maintainer="Iniity Engineering Team <dev@iniity.com>"' in dockerfile_content
    assert 'LABEL description="Proprietary AI Agent by Iniity Inc."' in dockerfile_content # Matches rebrand.py
    assert 'LABEL version="1.0.0"' in dockerfile_content


def test_fastapi_app_info_rebranding():
    """
    Checks branding in src/main.py FastAPI app instantiation.
    This involves parsing the Python file, which can be brittle.
    A better test would be to check the /openapi.json or /docs if running the server.
    For now, a simple string check.
    """
    main_py_path = Path("src/main.py")
    assert main_py_path.exists(), "src/main.py should exist"
    main_py_content = main_py_path.read_text(encoding="utf-8")

    assert 'title="Iniity AI Agent API"' in main_py_content
    assert 'description="Proprietary Anomaly Detection System by Iniity Inc."' in main_py_content
    assert '"name": "Iniity Support"' in main_py_content
    assert '"url": "https://www.iniity.com/support"' in main_py_content
    assert '"email": "support@iniity.com"' in main_py_content

    # Check the /api/v1/info endpoint's content as defined in main.py
    assert '"system": "Iniity AI Agent"' in main_py_content # From system_info()
    assert '"author": "Iniity Inc."' in main_py_content      # From system_info()
    assert '"repository": "https://git.iniity.com/IniitySovereignAgent.git"' in main_py_content # From system_info()

# Note: To fully verify the rebranding, one would typically:
# 1. Run the `scripts/rebrand.py` script.
# 2. Run the `scripts/cleanup-assets.sh` script (after configuring asset paths).
# 3. Manually update files like pyproject.toml if used.
# 4. Then run these tests.
# These tests primarily check if the constants and direct file overwrites I've performed are correct.
