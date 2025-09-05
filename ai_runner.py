import json
import subprocess
import sys
import os
from jinja2 import Template

def run_command(command):
    """Executes a shell command and prints its output in real-time."""
    print(f"Executing: {command}")
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
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

def configure_app(manifest):
    """Reads variables from the manifest, prompts the user, and generates config files."""
    config_path = 'config/config.py'
    template_path = 'config/config.py.tpl'

    if os.path.exists(config_path):
        print(f"Configuration file '{config_path}' already exists. Skipping configuration.")
        return

    if not os.path.exists(template_path):
        print(f"Error: Template file '{template_path}' not found. Cannot configure application.")
        sys.exit(1)

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

    with open(config_path, 'w') as f:
        f.write(rendered_config)

    print(f"Successfully created configuration file at '{config_path}'.")
    print("-----------------------------\n")


def main():
    """Main function to read manifest and run setup/application."""
    manifest_path = 'runner.json'

    if not os.path.exists(manifest_path):
        print(f"Error: {manifest_path} not found.")
        sys.exit(1)

    with open(manifest_path, 'r') as f:
        manifest = json.load(f)

    # --- New Configuration Step ---
    configure_app(manifest)

    print(f"--- Starting setup for {manifest['name']} ---")

    if 'setup' in manifest and isinstance(manifest['setup'], list):
        for command in manifest['setup']:
            run_command(command)

    print(f"--- Setup complete. Running application ---")

    if 'run' in manifest and 'default' in manifest['run']:
        run_command(manifest['run']['default'])
    else:
        print("Error: No default run command found in manifest.")
        sys.exit(1)

    print("--- Application run finished ---")

if __name__ == "__main__":
    main()
