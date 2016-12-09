### Logstash version
if [ -z "$1" ]; then
  echo ""
  echo "  Please specify the Logstash version you want to install!"
  echo ""
  echo "    $ $0 1.5.3"
  echo ""
  exit 1
fi
 
LOGSTASH_VERSION=$1
 
if [[ ! "${LOGSTASH_VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+ ]]; then
  echo ""
  echo "  The specified Logstash version isn't valid!"
  echo ""
  echo "    $ $0 1.5.3"
  echo ""
  exit 2
fi

LOGSTASH_DIRECTORY=logstash-${LOGSTASH_VERSION}
### Download and Install Logstash
curl -L https://download.elastic.co/logstash/logstash/${LOGSTASH_DIRECTORY}.tar.gz | tar -xz
CURRENT_DIR=${PWD}
PARENT_DIR="$(dirname "$CURRENT_DIR")"
LOGS_DIR=${PARENT_DIR}/logs/miebach_info.log


read -d '' LOGSTASH_CONF <<EOF
input {
  file {
    path => "$LOGS_DIR"
    start_position => "beginning"
  }
}
filter {
  if [path] =~ "access" {
    grok {
      match => { "message" => "%{DATESTAMP_EVENTLOG:timestamp} - %{DATA:data} - %{WORD:method} - %{DATA:report_data}" }
      overwrite => [ "message" ]
    }
  }
}
output {
  elasticsearch { host => localhost }
  stdout { codec => rubydebug }
}
EOF

cd ./${LOGSTASH_DIRECTORY}/bin/

echo "$LOGSTASH_CONF" >> logstash.conf

./logstash agent -f logstash.conf &
