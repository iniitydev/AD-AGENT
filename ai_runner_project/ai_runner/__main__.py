import json
import subprocess
import sys
import os
import argparse
import tempfile
import shutil
from urllib.parse import urlparse
from jinja2 import Template

def is_url(path):
    """Checks if a given path is a URL."""
    try:
        result = urlparse(path)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

def run_command(command, cwd):
    """Executes a shell command in a specific directory and prints its output."""
    print(f"Executing in '{cwd}': {command}")
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=cwd  # Run the command in the context of the repo root
        )
        for line in process.stdout:
            print(line, end='')
        process.wait()
        if process.returncode != 0:
            print(f"\nError: Command returned non-zero exit code {process.returncode}")
            sys.exit(1)
    except Exception as e:
        print(f"An error occurred while executing command: {command}")
        print(f"Error: {e}")
        sys.exit(1)
    print("\n")

def configure_app(repo_root, manifest):
    """Reads variables from the manifest, prompts the user, and generates config files."""
    config_path = os.path.join(repo_root, 'config/config.py')
    template_path = os.path.join(repo_root, 'config/config.py.tpl')

    if os.path.exists(config_path):
        print(f"Configuration file '{config_path}' already exists. Skipping configuration.")
        return

    if not os.path.exists(template_path):
        # This is not a fatal error, as not all projects need templating.
        print(f"Template file '{template_path}' not found. Skipping template rendering.")
        return

    print("--- Configuring Application ---")

    config_values = {}
    if 'variables' in manifest and isinstance(manifest['variables'], list):
        for var in manifest['variables']:
            prompt = f"{var['description']}: "
            user_input = input(prompt)
            config_values[var['name']] = user_input if user_input else var['default']

    with open(template_path, 'r') as f:
        template_content = f.read()

    template = Template(template_content)
    rendered_config = template.render(config_values)

    # Ensure the target directory exists
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    with open(config_path, 'w') as f:
        f.write(rendered_config)

    print(f"Successfully created configuration file at '{config_path}'.")
    print("-----------------------------\n")

def main():
    """Main entry point for the ai-runner tool."""
    parser = argparse.ArgumentParser(description="A universal runner for AI projects.")
    parser.add_argument("repo", help="Path to a local repository or a git URL.")
    args = parser.parse_args()

    repo_root = None
    temp_dir = None

    try:
        if is_url(args.repo):
            temp_dir = tempfile.mkdtemp()
            print(f"Cloning repository from '{args.repo}' into '{temp_dir}'...")
            run_command(f"git clone {args.repo} .", cwd=temp_dir)
            repo_root = temp_dir
        elif os.path.isdir(args.repo):
            repo_root = args.repo
            print(f"Running on local repository at '{repo_root}'...")
        else:
            print(f"Error: '{args.repo}' is not a valid git URL or local directory.")
            sys.exit(1)

        manifest_path = os.path.join(repo_root, 'runner.json')
        if not os.path.exists(manifest_path):
            print(f"Error: 'runner.json' not found in the root of the repository.")
            sys.exit(1)

        with open(manifest_path, 'r') as f:
            manifest = json.load(f)

        configure_app(repo_root, manifest)

        print(f"--- Starting setup for {manifest['name']} ---")
        if 'setup' in manifest and isinstance(manifest['setup'], list):
            for command in manifest['setup']:
                run_command(command, cwd=repo_root)

        print(f"--- Setup complete. Running application ---")
        if 'run' in manifest and 'default' in manifest['run']:
            run_command(manifest['run']['default'], cwd=repo_root)
        else:
            print("Error: No default run command found in manifest.")
            sys.exit(1)

        print("--- Application run finished ---")

    finally:
        if temp_dir:
            print(f"Cleaning up temporary directory '{temp_dir}'...")
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    main()
