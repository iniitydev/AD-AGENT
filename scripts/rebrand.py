# save as rebrand.py
import os
import re
from pathlib import Path

# CONFIGURATION - SET THESE VALUES
REPLACEMENTS = {
    "OriginalProjectName": "YourCompanyAgent", # Example, user should update
    "original_author": "Your Engineering Team", # Example
    "old-contact@email": "support@yourcompany.com", # Example
    "old-domain.com": "yourproduct.com", # Example
    # Add more specific replacements from the project if known
    # e.g., "Sovereign Anomaly Detection Agent": "YourCompany Proprietary Agent"
    # "iniity.com": "yourcompany.com"
    # "dev@iniity.com": "dev@yourcompany.com"
}

# More specific replacements based on previous Dockerfile/main.py content
REPLACEMENTS.update({
    "Sovereign Anomaly Detection Agent by iniity.com": "Proprietary AI Agent by YourCompany",
    "Sovereign Anomaly Detection Agent": "YourCompany AI Agent", # Broader replacement
    "dev@iniity.com": "dev@yourcompany.com", # From Dockerfile maintainer
    "iniity.com": "yourcompany.com" # General domain replacement
})


EXCLUDE_DIRS = {'.git', '__pycache__', 'venv', '.idea', 'docs/MSL', 'data/MSL', 'figs'} # Added some from existing structure
FILE_TYPES = {'.py', '.md', '.html', '.js', '.css', '.yml', '.toml', '.json', '.sh'} # Added .json, .sh

def rebrand_file(path: Path):
    try:
        content = path.read_text(encoding='utf-8')
        original_content = content # For checking if changes were made

        for old, new in REPLACEMENTS.items():
            # Use re.escape to handle special characters in 'old' string
            # Using word boundaries (\b) might be too restrictive for some replacements (like URLs or email parts)
            # Consider if simple string replace or more complex regex is needed for each case.
            # For now, using simple replace which is broader.
            # content = re.sub(rf'\b{re.escape(old)}\b', new, content) # Word boundary version
            content = content.replace(old, new)

        if content != original_content:
            path.write_text(content, encoding='utf-8')
            print(f"✓ Updated {path}")
        # else:
            # print(f"▫️ No changes for {path}")

    except UnicodeDecodeError:
        print(f"⨉ Skipped binary or non-UTF-8 file: {path}")
    except Exception as e:
        print(f"⚠️ Error processing file {path}: {e}")


def main():
    # Assume script is in project_root/scripts/ directory
    project_root = Path(__file__).parent.parent
    print(f"Project root identified as: {project_root}")

    processed_count = 0
    for file_path in project_root.glob('**/*'):
        if file_path.is_file() and file_path.suffix.lower() in FILE_TYPES:
            # Check if any part of the path contains an excluded directory name
            if not any(excluded_dir in file_path.parts for excluded_dir in EXCLUDE_DIRS):
                rebrand_file(file_path)
                processed_count += 1
            # else:
                # print(f"Skipping {file_path} due to exclude rule.")

    # Special files at project root that might not have extensions in FILE_TYPES
    # (e.g., LICENSE, Dockerfile, Makefile)
    # The glob '**/*' already includes these if they don't have extensions that are filtered out.
    # However, let's explicitly process them if they are not caught by suffix check.

    # The user's original script had a specific list. Let's refine.
    # We should process all files not in EXCLUDE_DIRS, then filter by FILE_TYPES if it's restrictive,
    # OR process all files not in EXCLUDE_DIRS and just try to read them as text.
    # The current glob includes files with extensions. Files like 'LICENSE' might be missed.

    # Let's ensure common non-extension config files are also processed if they exist.
    additional_files_to_check = ["LICENSE", "Makefile", "Dockerfile", ".env.example", ".gitignore", ".dockerignore", ".flake8", ".pre-commit-config.yaml"]
    for fname in additional_files_to_check:
        fpath = project_root / fname
        if fpath.exists() and fpath.is_file():
             if not any(excluded_dir in fpath.parts for excluded_dir in EXCLUDE_DIRS):
                # Check if already processed by glob if it had a suffix in FILE_TYPES
                # This is a bit redundant if FILE_TYPES is broad, but safe.
                # For simplicity, just call rebrand_file; it checks for actual content change.
                rebrand_file(fpath)
                processed_count+=1 # Count it if processed, though might be counted by glob too.

    print(f"Total files considered for rebranding (matching types/names): approx {processed_count}")


if __name__ == "__main__":
    print("🚀 Starting rebranding process...")
    print(f"Using replacements: {json.dumps(REPLACEMENTS, indent=2)}")
    main()
    print("✅ Rebranding script execution complete! Review changes carefully before committing.")
    print("   Remember to manually update pyproject.toml if you use it, and other project-specific config files.")
