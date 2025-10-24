#!/bin/bash
set -e

# Install composer dependencies if needed
if [ ! -d "vendor" ]; then
    echo "Installing composer dependencies..."
    composer install --quiet --no-interaction --no-dev --prefer-dist
fi

# Execute the PHP script with all arguments
exec php script.php "$@"
