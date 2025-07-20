#!/bin/sh
echo "Substituting environment variables in tools.yaml..."

# Use sed to replace environment variable placeholders with actual values
sed "s/\${DB_HOST}/$DB_HOST/g; s/\${DB_NAME}/$DB_NAME/g; s/\${DB_USER}/$DB_USER/g; s/\${DB_PASSWORD}/$DB_PASSWORD/g" /tools.yaml.template > /tools.yaml

echo "Generated tools.yaml:"
cat /tools.yaml

echo "Starting toolbox with processed configuration..."
exec /toolbox --tools-file /tools.yaml --address 0.0.0.0
