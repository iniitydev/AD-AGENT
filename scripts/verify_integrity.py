# scripts/verify_integrity.py
import hashlib
import json
import os
import click
from pathlib import Path

# Configuration
MANIFEST_FILE_NAME = "sovereign_manifest.json"
DEFAULT_EXCLUDES = {
    ".git",
    "__pycache__",
    ".DS_Store",
    "*.pyc",
    "*.pyo",
    ".pytest_cache",
    ".mypy_cache",
    ".idea",
    ".vscode",
    "build",
    "dist",
    "*.egg-info",
    ".env",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "data", # Often excluded if data is large or managed separately
    "models", # Often excluded if models are large or managed separately
    MANIFEST_FILE_NAME, # Exclude the manifest file itself from hashing
    "*.log",
    "logs"
}
HASH_ALGORITHM = "sha256"

def calculate_hash(filepath, algorithm=HASH_ALGORITHM):
    """Calculates the hash of a file."""
    h = hashlib.new(algorithm)
    try:
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except IOError:
        click.echo(click.style(f"Error: Could not read file {filepath}", fg="red"), err=True)
        return None

def should_exclude(path_str, project_root, exclude_patterns):
    """Checks if a path matches any exclude patterns."""
    # Normalize path relative to project root for consistent matching
    try:
        relative_path = path_str.relative_to(project_root)
    except ValueError: # path_str is not under project_root, should not happen if called correctly
        relative_path = path_str

    for pattern in exclude_patterns:
        if relative_path.match(pattern) or any(p.match(pattern) for p in relative_path.parents):
            return True
        # Also check if the pattern is a direct name match for files/dirs
        if pattern == path_str.name:
            return True
    return False

def generate_manifest(project_root_str=".", manifest_path_str=MANIFEST_FILE_NAME, exclude_list=None):
    """Generates a manifest file for all files in the project root."""
    project_root = Path(project_root_str).resolve()
    manifest_path = project_root / manifest_path_str

    if exclude_list is None:
        excludes = DEFAULT_EXCLUDES
    else:
        excludes = DEFAULT_EXCLUDES.union(set(exclude_list))

    click.echo(f"Generating manifest for project root: {project_root}")
    click.echo(f"Excluding patterns/files: {excludes}")

    manifest_data = {"algorithm": HASH_ALGORITHM, "files": {}}

    for path in project_root.rglob("*"):
        if path.is_file():
            # Use Path objects for should_exclude
            if should_exclude(path, project_root, excludes):
                # click.echo(f"Excluding {path.relative_to(project_root)}")
                continue

            file_hash = calculate_hash(path)
            if file_hash:
                relative_path_str = str(path.relative_to(project_root))
                manifest_data["files"][relative_path_str] = file_hash
                # click.echo(f"Hashed {relative_path_str}: {file_hash}")

    try:
        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f, indent=4, sort_keys=True)
        click.echo(click.style(f"Manifest generated successfully at {manifest_path}", fg="green"))
    except IOError:
        click.echo(click.style(f"Error: Could not write manifest file to {manifest_path}", fg="red"), err=True)

def verify_manifest(project_root_str=".", manifest_path_str=MANIFEST_FILE_NAME, exclude_list=None):
    """Verifies the integrity of files against the manifest."""
    project_root = Path(project_root_str).resolve()
    manifest_path = project_root / manifest_path_str

    if exclude_list is None:
        excludes = DEFAULT_EXCLUDES
    else:
        excludes = DEFAULT_EXCLUDES.union(set(exclude_list))

    click.echo(f"Verifying integrity for project root: {project_root}")
    click.echo(f"Using manifest: {manifest_path}")

    if not manifest_path.exists():
        click.echo(click.style(f"Error: Manifest file not found at {manifest_path}", fg="red"), err=True)
        click.echo(click.style("Please generate the manifest first using 'python scripts/verify_integrity.py generate'", fg="yellow"))
        return False

    try:
        with open(manifest_path, "r") as f:
            manifest_data = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        click.echo(click.style(f"Error: Could not read or parse manifest file: {e}", fg="red"), err=True)
        return False

    if manifest_data.get("algorithm") != HASH_ALGORITHM:
        click.echo(click.style(f"Warning: Manifest uses algorithm {manifest_data.get('algorithm')}, script uses {HASH_ALGORITHM}.", fg="yellow"))
        # Potentially adapt or fail here based on policy

    all_ok = True
    verified_files = set()

    for path in project_root.rglob("*"):
        if path.is_file():
            if should_exclude(path, project_root, excludes):
                continue

            relative_path_str = str(path.relative_to(project_root))
            verified_files.add(relative_path_str)

            current_hash = calculate_hash(path)
            if not current_hash: # Error reading file
                all_ok = False
                continue

            if relative_path_str not in manifest_data["files"]:
                click.echo(click.style(f"Untracked file: {relative_path_str}", fg="yellow"))
                all_ok = False # Or treat as warning based on policy
            elif manifest_data["files"][relative_path_str] != current_hash:
                click.echo(click.style(f"Tampered file: {relative_path_str} (expected {manifest_data['files'][relative_path_str]}, got {current_hash})", fg="red"))
                all_ok = False
            # else:
                # click.echo(f"OK: {relative_path_str}")


    # Check for missing files that are in manifest but not on disk
    manifest_file_set = set(manifest_data["files"].keys())
    missing_files = manifest_file_set - verified_files
    for missing_file in missing_files:
        # Check if the missing file itself is in the exclude list (e.g. if it was deleted and then added to excludes)
        # This check is a bit tricky because 'missing_file' is relative.
        # A simpler approach is to rely on the fact that rglob won't find it, so it won't be in verified_files.
        click.echo(click.style(f"Missing file: {missing_file} (listed in manifest but not found on disk)", fg="red"))
        all_ok = False


    if all_ok:
        click.echo(click.style("✅ Integrity check passed. All files match the manifest.", fg="green"))
    else:
        click.echo(click.style("❌ Integrity check failed. Some files do not match the manifest or are untracked/missing.", fg="red"))

    return all_ok


@click.group()
def cli():
    """Manages and verifies the sovereign manifest for code integrity."""
    pass

@cli.command()
@click.option('--root', default='.', help='Project root directory.', type=click.Path(exists=True, file_okay=False, resolve_path=True))
@click.option('--manifest-file', default=MANIFEST_FILE_NAME, help='Name of the manifest file.')
@click.option('--exclude', multiple=True, help='Patterns or filenames to exclude from hashing.')
def generate(root, manifest_file, exclude):
    """Generates the sovereign_manifest.json file."""
    generate_manifest(root, manifest_file, list(exclude))

@cli.command()
@click.option('--root', default='.', help='Project root directory.', type=click.Path(exists=True, file_okay=False, resolve_path=True))
@click.option('--manifest-file', default=MANIFEST_FILE_NAME, help='Name of the manifest file.')
@click.option('--exclude', multiple=True, help='Patterns or filenames to exclude (must match generation).')
def verify(root, manifest_file, exclude):
    """Verifies files against the sovereign_manifest.json."""
    if not verify_manifest(root, manifest_file, list(exclude)):
        exit(1) # Exit with error code if verification fails

if __name__ == "__main__":
    cli()
