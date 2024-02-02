#!/bin/bash

if [ $# -eq  0 ]; then
	echo Usage: ms-chatbot.sh tenant
	exit 1
fi

TENANT_NUMBER=$1

# Check that the tenant number is not empty and a number
if [ -z "$TENANT_NUMBER" ] || ! [[ "$TENANT_NUMBER" =~ ^[0-9]+$ ]]
then
    echo "Please provide a tenant number as the first argument"
    exit 1
fi

export WEAVIATE_TENANT='tenant_'$TENANT_NUMBER


# Check if VERBA_PORT or STREAMLIT_PORT is empty
if [ -z "$VERBA_PORT" ] || [ -z "$STREAMLIT_PORT" ]
then
    echo "VERBA_PORT or STREAMLIT_PORT is empty. Please make sure the values are defined in env variables."
    exit 1
fi

echo $WEAVIATE_URL_VERBA

# Function to kill children processes when the main script is killed
kill_children_processes() {
    pkill -P $$
}
trap 'kill_children_processes; exit' INT TERM
set -m

# Start Verba
echo "Starting Verba on port $VERBA_PORT..."
(verba start --port $VERBA_PORT) &
echo "Verba started"

# Start Streamlit
echo "Starting Streamlit on port $STREAMLIT_PORT (url will be http://localhost:$STREAMLIT_PORT)..."
(python3 -m streamlit run streamlit_rag/app.py --server.port $STREAMLIT_PORT --server.headless true --theme.base dark --theme.primaryColor "4db8a7" -- --verba_port $VERBA_PORT --verba_base_url $BASE_VERBA_API_URL --chunk_size $CHUNK_SIZE) &
echo "Streamlit started"

wait
