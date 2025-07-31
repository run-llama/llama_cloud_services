# create uv virtual environment
uv venv
source .venv/bin/activate

# install toml
uv pip install -r scripts/requirements.txt

# run version change
uv run -- python3 scripts/new_version.py

# test version change
status_code=$(uv run -- python3 scripts/test_new_version.py) # returns 0 if the versions are the same, 1 if they are not

if [ "$status_code" -eq 1 ]; then
   echo "Versions do not match, the version change failed..."
   exit 1
elif [ "$status_code" -eq 0 ]; then
   # lock the version changes
   uv lock && cd llama_parse/ && uv lock
   echo "Versions successfully changed"
   exit 0
fi
