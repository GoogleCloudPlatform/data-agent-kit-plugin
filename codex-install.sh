#!/bin/bash
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -e

TAG=$1

PLUGIN_NAME="data-agent-kit-starter-pack"
REPO_URL="https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack"
INSTALL_DIR="$HOME/.agents/plugins/$PLUGIN_NAME"
MARKETPLACE_FILE="$HOME/.agents/plugins/marketplace.json"

echo "--- $PLUGIN_NAME Installer for Codex ---"

# Prompt for configuration variables
echo "Please enter the following configuration variables:"
echo "GCP Project ID"
read -p "Project ID when using the MCP toolbox for databases: " PROJECT_ID </dev/tty

echo "GCP Region"
read -p "Region for GCP services (e.g. us-west1): " GCP_REGION </dev/tty

echo "BigQuery Location"
read -p "Location for BigQuery datasets (e.g. US): " BIGQUERY_LOCATION </dev/tty

# 1. Download/Update Plugin Content
mkdir -p "$HOME/.agents/plugins"
if [ -d "$INSTALL_DIR" ]; then
    BACKUP_DIR="${INSTALL_DIR}_backup_$(date +%Y%m%d_%H%M%S)"
    echo "Backing up existing plugin to $BACKUP_DIR..."
    mv "$INSTALL_DIR" "$BACKUP_DIR"
    echo "Notice: Your previous installation has been backed up to $BACKUP_DIR."
    echo "You can delete it if you do not need it."
fi

if [ -n "$TAG" ]; then
    echo "Cloning plugin version $TAG to $INSTALL_DIR..."
    git clone --depth 1 --branch "$TAG" "$REPO_URL" "$INSTALL_DIR"
else
    echo "Cloning plugin default branch to $INSTALL_DIR..."
    git clone --depth 1 "$REPO_URL" "$INSTALL_DIR"
fi

echo "Removing git metadata..."
rm -rf "$INSTALL_DIR/.git"

echo "Applying configuration..."
node -e "
const fs = require('fs');
const path = require('path');
const mcpFilePath = path.join(process.argv[1], 'mcp.json');
let mcpContent = fs.readFileSync(mcpFilePath, 'utf8');
mcpContent = mcpContent.replace(/\\\$PROJECT_ID/g, process.argv[2]);
mcpContent = mcpContent.replace(/\\\$GCP_REGION/g, process.argv[3]);
mcpContent = mcpContent.replace(/\\\$BIGQUERY_LOCATION/g, process.argv[4]);
fs.writeFileSync(mcpFilePath, mcpContent);
" "$INSTALL_DIR" "$PROJECT_ID" "$GCP_REGION" "$BIGQUERY_LOCATION"

# 2. Register with Codex Marketplace
if [ ! -f "$MARKETPLACE_FILE" ]; then
    echo "Creating new personal marketplace..."
    echo '{"name": "personal", "plugins": []}' > "$MARKETPLACE_FILE"
fi

echo "Registering plugin in $MARKETPLACE_FILE..."
node -e "
const fs = require('fs');
const path = require('path');
const file = path.resolve(process.env.HOME, '.agents/plugins/marketplace.json');
let data;
try {
    data = JSON.parse(fs.readFileSync(file, 'utf8'));
} catch (e) {
    data = { name: 'personal', plugins: [] };
}
data.plugins = data.plugins || [];
data.plugins = data.plugins.filter(p => p.name !== '${PLUGIN_NAME}');
data.plugins.push({
    name: '${PLUGIN_NAME}',
    interface: { displayName: 'Data Agent Kit Starter Pack' },
    source: { source: 'local', path: './.agents/plugins/${PLUGIN_NAME}' },
    policy: { installation: 'AVAILABLE', authentication: 'ON_INSTALL' },
    category: 'Productivity'
});
fs.writeFileSync(file, JSON.stringify(data, null, 2));
"

echo "Done! Restart Codex to use the $PLUGIN_NAME plugin."
