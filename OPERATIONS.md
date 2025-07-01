# Operations Guide

This document outlines operational procedures for managing the **Iniity Sovereign AI Agent** repository, particularly for administrative tasks like repository detachment from a fork and history sanitization.

## 1. Detaching Repository from an Upstream Fork

If this repository was originally forked and you wish to make it a standalone repository, follow these steps carefully.

**⚠️ Critical Prerequisites:**

1.  **BACKUP YOUR REPOSITORY:** Before performing any of these operations, ensure you have a full backup of your repository (e.g., clone it to a separate, safe location, or ensure your latest changes are pushed to a secure branch/remote). These operations, especially `git filter-repo` and force pushing, are destructive.
2.  **Install `git-filter-repo`:** This tool is recommended for rewriting history and is generally safer and easier to use than `git filter-branch`. Installation instructions: [https://github.com/newren/git-filter-repo/blob/main/INSTALL.md](https://github.com/newren/git-filter-repo/blob/main/INSTALL.md)
3.  **Install GitHub CLI (`gh`):** Required for the `gh repo fork --unfork` command if you are using GitHub and want to remove the fork relationship via their API. Install from [https://cli.github.com/](https://cli.github.com/).

### Step-by-Step Detachment Procedure:

1.  **Verify Current Remotes:**
    Check your current remote repositories. You will likely see `origin` (your fork) and `upstream` (the original repository).
    ```bash
    git remote -v
    ```

2.  **Remove Upstream Connection:**
    This removes the link to the original upstream repository.
    ```bash
    git remote remove upstream
    ```
    Verify again with `git remote -v`. Only `origin` should remain.

3.  **Create a New Blank Repository on Your Company's Git Server:**
    Go to your company's Git hosting platform (e.g., your internal GitLab, GitHub Enterprise, or a new repository on github.com under your company's organization like `Iniity`). Create a new, empty repository. For example, name it `IniitySovereignAgent`.
    **Do NOT initialize it with a README, .gitignore, or license.**

4.  **Reset Origin to Your New Repository:**
    Update the `origin` remote to point to your new repository URL.
    Replace `https://git.iniity.com/IniitySovereignAgent.git` with the actual URL of your new repository.
    ```bash
    git remote set-url origin https://git.iniity.com/IniitySovereignAgent.git
    ```
    Verify with `git remote -v`.

5.  **Remove Fork Metadata / Clean History (Optional but Recommended):**
    If you want to completely sever the history from the original fork and make it appear as if your repository is the true origin, `git filter-repo` can be used. The command `git filter-repo --replace-refs delete-no-add` is mentioned by the user, but its exact effect should be understood from its documentation. A common use of `filter-repo` for this purpose is to simply process the repo without specific filters, which can help clean up internal Git data.

    A more direct approach to ensure only your desired history is pushed is to carefully manage branches. If you want to start "fresh" on the new remote, you might push only specific branches.

    *If you used `gh repo fork --unfork` (see step 7b), this step might be less critical from GitHub's perspective, but `filter-repo` can still be useful for cleaning local history if desired.*

    **Caution:** `git filter-repo` rewrites history. Ensure all collaborators are aware and have pushed their changes.

6.  **Push to New Origin:**
    Push all branches and tags to your new repository. The `--force` flag is typically needed because you are overwriting the (potentially empty) history of the new repository.
    ```bash
    git push --all --force
    git push --tags --force
    ```

7.  **Verify Detachment & GitHub Specifics:**

    a.  **Local Verification:**
        Check the commit history. It should reflect your repository's history.
        ```bash
        git log --graph --oneline
        ```

    b.  **GitHub - Remove Fork Relationship (Using GitHub CLI):**
        If your new repository is on GitHub and was initially created as a fork on GitHub (even if you've changed remotes), you might want to use the GitHub CLI to completely detach it from the original upstream network, turning it into a standalone repository.
        ```bash
        gh repo fork --unfork
        ```
        This command needs to be run from within the local repository directory. It will prompt you to confirm.

    c.  **GitHub - View Repository Status:**
        After running `--unfork` (if applicable), you can view the repository details:
        ```bash
        gh repo view
        ```
        This should no longer show it as "forked from...".

## 2. History Sanitization (Advanced)

If there's sensitive information or old branding/email addresses in commit messages or file content throughout the history that you need to remove, `git filter-repo` is a powerful tool.

**⚠️ Extreme Caution:** Rewriting history is a destructive operation. Ensure you understand the implications and have a backup. All collaborators will need to re-clone or perform complex `git pull` operations after history is rewritten on the remote.

**Example: Replacing Text in History:**
To replace all occurrences of `old-sensitive-text` with `new-safe-text` in all historical files and commit messages:
```bash
# First, create a "mailmap" if you need to consolidate author identities
# echo "New Name <new@email.com> Old Name <old@email.com>" > .mailmap
# git filter-repo --mailmap .mailmap

# To replace text:
# Create a file, e.g., replacements.txt:
# old-domain.com==>new-iniity.com
# old-project-name==>IniitySovereignAgent
# old-contact@example.com==>contact@iniity.com

git filter-repo --replace-text replacements.txt --force
```
Refer to the `git filter-repo` documentation for detailed usage and safety measures. After running, you will need to force push all branches and tags again:
```bash
git push --all --force
git push --tags --force
```

## 3. Post-Rebranding Verification

After all rebranding steps (including running `scripts/rebrand.py` and `scripts/cleanup-assets.sh`):

1.  **Inspect Changes:** Manually review all changes made by scripts and manual edits.
2.  **Run Test Suite:** Execute the full test suite (`make test` or `python -m pytest tests -v`).
3.  **CI/CD Pipelines:** Ensure CI/CD pipelines are updated to point to the new repository URL and use any new secrets or environment variables.
4.  **Domain and Links:** Verify that all public-facing documentation, links within the application, and domain configurations point to the new Iniity-branded URLs and resources.

This operations guide should be reviewed and adapted based on the specifics of your Git hosting and deployment environment.You are currently working on plan step: Document Repository Detachment & History Sanitization:. Once you have finished this, call `plan_step_complete()` before moving on to the next step.
