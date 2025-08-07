# initialize pypi_token
pypi_token="no_token"

while
    [[ $# -gt 0 ]] \
        ;
do
    case "$1" in
    -t | --token)
        pypi_token="$2"
    esac
done

if [[ $pypi_token == "no_token" ]]; then
    if [[ $LLAMA_PARSE_PYPI_TOKEN == "" ]]; then
        echo "No token provided and no token in the environment, exiting..."
        exit 1
    else
        pypi_token="$LLAMA_PARSE_PYPI_TOKEN"
    fi
fi

# check pre-release
uv venv && source .venv/bin/activate && uv pip install -r scripts/requirements.txt
do_not_release=$(python3 scripts/pre_release_check.py)

if [ "$do_not_release" -eq 1 ]; then
   echo "Nothing to release"
   exit 0
else
    # build and publish llama_cloud_services
    ## build
    uv build
    ## publish
    uv publish --token $pypi_token
fi
