import json
import subprocess
import sys
import os

def run_command(command):
    """Executes a shell command and prints its output in real-time."""
    print(f"Executing: {command}")
    try:
        # Using Popen to stream output in real-time
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        # Read and print output line by line
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

def main():
    """Main function to read manifest and run setup/application."""
    manifest_path = 'runner.json'

    if not os.path.exists(manifest_path):
        print(f"Error: {manifest_path} not found.")
        sys.exit(1)

    with open(manifest_path, 'r') as f:
        manifest = json.load(f)

    print(f"--- Starting setup for {manifest['name']} ---")

    # Execute setup commands
    if 'setup' in manifest and isinstance(manifest['setup'], list):
        for command in manifest['setup']:
            run_command(command)

    print(f"--- Setup complete. Running application ---")

    # Execute the default run command
    if 'run' in manifest and 'default' in manifest['run']:
        run_command(manifest['run']['default'])
    else:
        print("Error: No default run command found in manifest.")
        sys.exit(1)

    print("--- Application run finished ---")

if __name__ == "__main__":
    main()
