#!/bin/bash
# Get absolute path of this script's directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Starting Model Context Protocol (MCP) Inspector..."
echo "Pointing to server at: $DIR/mcp_server.py"

mkdir -p "$DIR/.npm-cache"
NPM_CONFIG_CACHE="$DIR/.npm-cache" npx -y @modelcontextprotocol/inspector uv run --with fastmcp python3 "$DIR/mcp_server.py"
