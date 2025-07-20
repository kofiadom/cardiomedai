#!/bin/sh
echo "=== MCP Toolbox Entrypoint ==="
echo "Current directory: $(pwd)"
echo "Files in root:"
ls -la /

echo "Environment variables:"
env | grep DB_ || echo "No DB_ variables found"

echo "Checking template file..."
if [ ! -f "/tools.yaml.template" ]; then
    echo "ERROR: Template file not found!"
    exit 1
fi

echo "Template content:"
cat /tools.yaml.template

echo "Substituting environment variables..."
envsubst < /tools.yaml.template > /tools.yaml || echo "envsubst failed"

echo "Checking if tools.yaml was created..."
if [ ! -f "/tools.yaml" ]; then
    echo "ERROR: tools.yaml was not created!"
    echo "Trying manual substitution..."
    sed "s/\${DB_HOST}/$DB_HOST/g; s/\${DB_NAME}/$DB_NAME/g; s/\${DB_USER}/$DB_USER/g; s/\${DB_PASSWORD}/$DB_PASSWORD/g" /tools.yaml.template > /tools.yaml
fi

echo "Final tools.yaml content:"
cat /tools.yaml

echo "Starting toolbox..."
exec /toolbox --tools-file /tools.yaml --address 0.0.0.0
