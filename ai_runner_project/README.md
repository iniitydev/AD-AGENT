# AI Runner

A universal, manifest-driven runner for setting up and running AI projects.

## Usage

This tool is designed to be installed as a standalone package. Once installed, you can run any AI project that contains a `runner.json` manifest file.

```bash
# Install the runner (example)
pip install .

# Run a project from a git repository
ai-runner https://github.com/some-user/some-ai-project

# Run a project from a local directory
ai-runner /path/to/local/project
```

## How it Works

The `ai-runner` reads a `runner.json` manifest file in the root of the target repository. This file defines:
-   Configuration variables to prompt the user for.
-   Setup commands to install dependencies.
-   Run commands to execute the application.

On the first run, it will interactively ask for configuration values and generate the necessary config files using a templating system. It will then install dependencies and run the project.
