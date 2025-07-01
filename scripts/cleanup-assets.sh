#!/bin/bash
# save as cleanup-assets.sh

echo "🚀 Starting asset cleanup and rebranding..."

# Define project root relative to the script location
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Project root: $PROJECT_ROOT"

# --- Configuration ---
NEW_COMPANY_NAME="Iniity Inc."
# Define paths for your new assets. These are placeholders.
# User should replace these with actual paths to their new logo and favicon
# or ensure the target files are placed correctly before running this.
# Example: NEW_LOGO_PATH="$PROJECT_ROOT/brand_assets/iniity_logo.svg"
NEW_LOGO_PATH="$PROJECT_ROOT/static/images/placeholder_iniity_logo.svg" # Defaulting to a placeholder name
NEW_FAVICON_URL="https://www.iniity.com/favicon.ico" # Placeholder URL for iniity.com

# Target asset locations
STATIC_IMAGES_DIR="$PROJECT_ROOT/static/images"
STATIC_DIR="$PROJECT_ROOT/static"
LICENSE_FILE="$PROJECT_ROOT/LICENSE"

# --- Asset Replacement ---

# 1. Replace logos
# This script assumes the new logo should be named 'logo.svg' in the target directory.
# User should place their actual 'iniity_logo.svg' (or similar) at $NEW_LOGO_PATH
# or update NEW_LOGO_PATH to point to their actual new logo file.
if [ -d "$STATIC_IMAGES_DIR" ]; then
    TARGET_LOGO_PATH="$STATIC_IMAGES_DIR/logo.svg"
    if [ -f "$NEW_LOGO_PATH" ]; then
        echo "Replacing logo at $TARGET_LOGO_PATH with $NEW_LOGO_PATH..."
        cp "$NEW_LOGO_PATH" "$TARGET_LOGO_PATH"
        echo "✓ Logo replaced. Make sure $NEW_LOGO_PATH was your intended new logo."
    else
        echo "⚠️ New logo source file at $NEW_LOGO_PATH not found."
        echo "   Please place your new logo there or update NEW_LOGO_PATH in this script."
        echo "   Attempting to use the existing static/images/logo.svg if it's the placeholder."
        if [ -f "$TARGET_LOGO_PATH" ]; then
            echo "   (Keeping existing $TARGET_LOGO_PATH for now)"
        else
            echo "   (No logo at $TARGET_LOGO_PATH to keep or replace)"
        fi
    fi
else
    echo "⚠️ Directory $STATIC_IMAGES_DIR not found. Skipping logo replacement."
fi

# 2. Update favicon.ico
if [ -d "$STATIC_DIR" ]; then
    TARGET_FAVICON_PATH="$STATIC_DIR/favicon.ico"
    echo "Attempting to download new favicon to $TARGET_FAVICON_PATH from $NEW_FAVICON_URL..."
    # Use curl with -f to fail silently on server errors, -L to follow redirects
    if curl -fL -o "$TARGET_FAVICON_PATH" "$NEW_FAVICON_URL"; then
        echo "✓ Favicon updated from $NEW_FAVICON_URL."
        if [ ! -s "$TARGET_FAVICON_PATH" ]; then # Check if file is empty
             echo "⚠️ Downloaded favicon is empty. URL might be incorrect or lead to an error page."
        fi
    else
        echo "⚠️ Failed to download favicon from $NEW_FAVICON_URL (curl exit code: $?). Please check URL or replace manually."
    fi
else
    echo "⚠️ Directory $STATIC_DIR not found. Skipping favicon update."
fi


# 3. Rebrand LICENSE file
if [ -f "$LICENSE_FILE" ]; then
    echo "Rebranding LICENSE file to MIT License with '$NEW_COMPANY_NAME'..."
    YEAR=$(date +%Y)
    # Using cat and EOL to prevent issues with special characters in typical license text
    cat > "$LICENSE_FILE" <<- EOL
MIT License

Copyright (c) $YEAR $NEW_COMPANY_NAME

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
EOL
    echo "✓ LICENSE file updated."
else
    echo "⚠️ LICENSE file not found at $LICENSE_FILE. Skipping license update."
fi

# 4. Remove old author-specific assets (example)
# This is a placeholder as per user's script; actual terms to find would be project-specific.
# It's safer to guide the user to do this manually or with more specific patterns.
echo "---"
echo "Asset Cleanup Note: The user's original script included a 'find ... -name '*original_author*' ...' command."
echo "This type of broad search-and-delete can be risky."
echo "Please manually review your project for any files specifically named with old branding terms"
echo "(e.g., 'old_company_logo.png', 'previous_author_notes.txt') and remove them if necessary."
echo "Skipping automatic removal of files based on generic terms like 'original_author'."
echo "---"


echo "✅ Asset cleanup and rebranding script execution finished."
echo "   IMPORTANT: Review all changes carefully."
echo "   - Ensure '$NEW_LOGO_PATH' pointed to your actual new logo file for replacement."
echo "   - Verify favicon was downloaded correctly from '$NEW_FAVICON_URL'."
echo "   - Manually review and remove any other old branding artifacts not covered by this script."
