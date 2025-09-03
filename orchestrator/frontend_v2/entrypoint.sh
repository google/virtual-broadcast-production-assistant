#!/bin/sh

echo "--- Printing all environment variables ---"
printenv
echo "--- End of environment variables ---"

# Exit with a non-zero code to make the container fail
# so we can inspect the logs.
exit 1