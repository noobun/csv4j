#!/bin/bash
# Check if -r flag is provided for release mode
if [ "$1" = "-r" ]; then
    RELEASE_MODE=true
fi

#source venv/bin/activate
echo -e "\nStart black..."
echo "######################"
black src/**.py

echo -e "\nStart ruff..."
echo "######################"
ruff check src/**.py

echo -e "\nStart flake..."
echo "######################"
flake8 src/**.py

echo -e "\nStart bandit..."
echo "######################"
bandit src/**.py

echo -e "\nStart mypy..."
echo "######################"
mypy --install-types
mypy src/**.py

echo -e "\nStart pytest..."
echo "######################"
pytest ./tests/test_main.py ./tests/test_payload.py -v --tb=no

if [ "$RELEASE_MODE" = true ]; then
    # Release mode: build, create venv, install wheel, and test
    python -m build --wheel
    if [ -d ".whl_test_env" ]; then
        rm -rf .whl_test_env
    fi
    python -m venv .whl_test_env
    source .whl_test_env/bin/activate
    pip install --quiet --upgrade pip
    pip install --quiet -r requirements.txt
    pip install --quiet dist/csv4j-*.whl pytest
    pytest ./tests/test_whl.py -v --tb=short
    deactivate
    rm -rf .whl_test_env
fi
