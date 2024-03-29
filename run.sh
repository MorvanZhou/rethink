# parse arguments to --mode, --reload, --host, --port
# default to local mode with reload, port=8000, host=127.0.0.1

# create help
help="Usage: run.sh [options]
Options:
  -h, --host      Set host, default to 127.0.0.1
  -p, --port      Set port, default to 8000
  -m, --mode      Set mode to local or production, personal use is restricted to local mode
  -r, --reload    Reload server on code change
  -h, --help      Show this help message and exit
"

# set mode
mode="local"
reload=""
host="127.0.0.1"
port="8000"


while [[ $# -gt 0 ]]
do
  key="$1"
  case $key in
    -h|--help)
      echo "$help"
      exit 0
      ;;
    -m|--mode)
      mode="$2"
      shift
      shift
      ;;
    -r|--reload)
      reload="--reload"
      shift
      ;;
    -h|--host)
      host="$2"
      shift
      shift
      ;;
    -p|--port)
      port="$2"
      shift
      shift
      ;;
    *)
      echo "Unknown option $key"
      exit 1
      ;;
  esac
done

export VUE_APP_API_PORT=$port
export VUE_APP_MODE=$mode
# if mode is local, export LOCAL_STORAGE_PATH to .data
if [ $mode == "local" ]; then
  export LOCAL_STORAGE_PATH=.
fi
echo "Running in $mode mode with reload=$reload on $host:$port"
# set working directory to rethink
uvicorn rethink.application:app $reload --host $host --port $port --env-file .env.$mode
