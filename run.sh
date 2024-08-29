# parse arguments to --mode, --reload, --host, --port
# default to local mode with reload, port=8000, host=127.0.0.1

# create help
help="Usage: run.sh [options]
Options:
  -h, --host      Set host, default to 127.0.0.1
  -p, --port      Set port, default to 8000
  -m, --mode      Set mode to local, dev or prod, personal use is restricted to local mode
  -r, --reload    Reload server on code change
  -h, --help      Show this help message and exit
  --password,      Set password for local mode
"

# set mode
mode="local"
reload=""
host="127.0.0.1"
port="8000"
password=""


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
    --password)
      password="$2"
      shift
      shift
      ;;
    *)
      echo "Unknown option $key"
      exit 1
      ;;
  esac
done

export VUE_APP_API_URL=http://$host:$port
export VUE_APP_MODE=$mode
# if mode is local, export RETHINK_LOCAL_STORAGE_PATH to .data
if [ $mode == "local" ]; then
  export RETHINK_LOCAL_STORAGE_PATH=.
  export RETHINK_SERVER_HEADLESS=1
  if [ $password != "" ]; then
    export RETHINK_LOCAL_PASSWORD=$password
  fi
fi
echo "Running in $mode mode with reload=$reload on $host:$port"
# set working directory to retk
uvicorn retk.application:app $reload --log-config log-config.json --host $host --port $port --env-file .env.$mode
