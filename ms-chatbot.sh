#!/bin/bash

if [ $# -eq  0 ]; then
	echo Usage: ms-chatbot.sh tenant
	exit 1
fi

TENANT_NUMBER=$1

export OPENAI_API_TYPE="azure"
export OPENAI_BASE_URL="https://wlgptpocrelay.azurewebsites.net"
export OPENAI_API_VERSION="2023-05-15"
export AZURE_OPENAI_RESOURCE_NAME="wlgptpocrelay"
export AZURE_OPENAI_EMBEDDING_MODEL="text-embedding-ada-002"
export VERBA_WAIT_TIME_BETWEEN_INGESTION_QUERIES_MS="200"
export WEAVIATE_URL_VERBA="http://localhost:8080"
export BASE_VERBA_API_URL="http://localhost"


# Check that the tenant number is not empty and a number
if [ -z "$TENANT_NUMBER" ] || ! [[ "$TENANT_NUMBER" =~ ^[0-9]+$ ]]
then
    echo "Please provide a tenant number as the first argument"
    exit 1
fi

export WEAVIATE_TENANT='tenant_'$TENANT_NUMBER

# Read values from the "tenant_mapping.csv" file
# We do +2 because TENANT number starts at 0, our csv file starts at 1 and we have the header to ignore
VERBA_PORT=$(awk -F ',' -v line=$((TENANT_NUMBER+2)) 'NR==line {print $1}' tenant_mapping.csv)
STREAMLIT_PORT=$(awk -F ',' -v line=$((TENANT_NUMBER+2)) 'NR==line {print $3}' tenant_mapping.csv)
CHUNK_SIZE=$(awk -F ',' -v line=$((TENANT_NUMBER+2)) 'NR==line {print $4}' tenant_mapping.csv)

export URL_PREFIX=$(awk -F ',' -v line=$((TENANT_NUMBER+2)) 'NR==line {print $2}' tenant_mapping.csv)
export OPENAI_MODEL=$(awk -F ',' -v line=$((TENANT_NUMBER+2)) 'NR==line {print $5}' tenant_mapping.csv)

# Check if VERBA_PORT or STREAMLIT_PORT is empty
if [ -z "$VERBA_PORT" ] || [ -z "$STREAMLIT_PORT" ] || [ -z "$URL_PREFIX" ]
then
    echo "VERBA_PORT or STREAMLIT_PORT or URL_PREFIX is empty. Please make sure the values are defined in the tenant_mapping.csv file."
    exit 1
fi

# Function to kill children processes when the main script is killed
kill_children_processes() {
    pkill -P $$
}
trap 'kill_children_processes; exit' INT TERM
set -m

# Start Verba, store standard and error logs in verba.$1.log, do not erase the previous logs
echo "Starting Verba on port $VERBA_PORT..."
(verba start --port $VERBA_PORT >> logs/verba.$1.log 2>&1) &
echo "Verba started"

# Start Streamlit, store standard and error logs in streamlit.$1.log, do not erase the previous logs
echo "Starting Streamlit on port $STREAMLIT_PORT (url will be http://localhost:$STREAMLIT_PORT/$URL_PREFIX)..."
(python3 -m streamlit run streamlit_rag/app.py --server.port $STREAMLIT_PORT --server.baseUrlPath "/${URL_PREFIX}/" --server.headless true --theme.base dark --theme.primaryColor "4db8a7" -- --verba_port $VERBA_PORT --verba_base_url $BASE_VERBA_API_URL --chunk_size $CHUNK_SIZE  >> logs/streamlit.$1.log 2>&1) &
echo "Streamlit started"

wait
