### Kibana version
if [ -z "$1" ]; then
  echo ""
  echo "  Please specify the Kibana version you want to install!"
  echo ""
  echo "    $ $0 4.1.1"
  echo ""
  exit 1
fi
 
KIBANA_VERSION=$1
 
if [[ ! "${KIBANA_VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+ ]]; then
  echo ""
  echo "  The specified Kibana version isn't valid!"
  echo ""
  echo "    $ $0 4.4.1"
  echo ""
  exit 2
fi

KIBANA_DIRECTORY=kibana-${KIBANA_VERSION}-linux-x64
### Download and Install Kibana
curl -L https://download.elastic.co/kibana/kibana/${KIBANA_DIRECTORY}.tar.gz | tar -xz
./${KIBANA_DIRECTORY}/bin/kibana &

### Make sure service is running
curl http://localhost:5601
