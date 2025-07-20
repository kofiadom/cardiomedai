#!/bin/sh
echo "=== MCP Toolbox Environment Variable Substitution ==="

# Check if all required environment variables are set
if [ -z "$DB_HOST" ] || [ -z "$DB_NAME" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ]; then
    echo "ERROR: Missing required environment variables"
    echo "Required: DB_HOST, DB_NAME, DB_USER, DB_PASSWORD"
    echo "DB_HOST: $DB_HOST"
    echo "DB_NAME: $DB_NAME"
    echo "DB_USER: $DB_USER"
    echo "DB_PASSWORD: [REDACTED]"
    exit 1
fi

echo "Environment variables found:"
echo "DB_HOST: $DB_HOST"
echo "DB_NAME: $DB_NAME"
echo "DB_USER: $DB_USER"
echo "DB_PASSWORD: [REDACTED]"

echo "Checking template file..."
if [ ! -f "/tools.yaml.template" ]; then
    echo "ERROR: Template file /tools.yaml.template not found"
    exit 1
fi

echo "Template content:"
cat /tools.yaml.template

echo "Substituting environment variables..."

# Use sed to replace environment variable placeholders with actual values
# Escape special characters in password for sed
DB_PASSWORD_ESCAPED=$(echo "$DB_PASSWORD" | sed 's/[[\.*^$()+?{|]/\\&/g')

sed -e "s/\${DB_HOST}/$DB_HOST/g" \
    -e "s/\${DB_NAME}/$DB_NAME/g" \
    -e "s/\${DB_USER}/$DB_USER/g" \
    -e "s/\${DB_PASSWORD}/$DB_PASSWORD_ESCAPED/g" \
    /tools.yaml.template > /tools.yaml

echo "Checking if tools.yaml was created..."
if [ ! -f "/tools.yaml" ]; then
    echo "ERROR: Failed to create /tools.yaml"
    exit 1
fi

echo "Generated configuration:"
cat /tools.yaml

echo "Starting MCP Toolbox..."
exec /toolbox --tools-file /tools.yaml --address 0.0.0.0
