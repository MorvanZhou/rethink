version=$(grep "^version" setup.cfg | awk -F'=' '{print $2}' | tr -d '[:space:]')
docker build -t morvanzhou/rethink:$version -t morvanzhou/rethink:latest .
