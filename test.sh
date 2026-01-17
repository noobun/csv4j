#!/bin/bash
# Parse flags: -r for release mode, -d to include directories starting
# with '__' when running payload tests. Export an env var consumed by
# the pytest loaders in `tests/`.
RELEASE_MODE=false
INCLUDE_DUNDERS=false
for arg in "$@"; do
    case "$arg" in
        -r)
            RELEASE_MODE=true
            ;;
        -d)
            INCLUDE_DUNDERS=true
            ;;
    esac
done

if [ "$INCLUDE_DUNDERS" = true ]; then
    export CSV4J_INCLUDE_DUNDERS=1
fi

rm dump/*
rm csv4j.log

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
pytest ./tests/test_main.py ./tests/test_payload.py ./tests/test_specials.py ./tests/test_cli.py -v #--tb=no

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
