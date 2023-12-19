# Streamlit RAG frontend

This package is meant to provide a streamlit front-end that uses the Verba API.

The streamlit pages are in `app_pages/`

The code utils are in `verba_utils/`

## Installation

To install the needed dependencies and the custom packages go to `Verba/streamlit_rag/` and run the command:

```bash
pip install -e .
```

## Start the app

To start the streamlit app :

Here are the CLI arguments:

**Argument directly used by streamlit :**

- `server.port` : the port on which you want your streamlit to run
- `server.baseUrlPath` : (optional) if you want to add a prefix in the streamlit url (eg `http://localhost:8500` with prefix `toto` becomes `http://localhost/toto:8500`)
- `server.headless` : set to `true` not to open a browser at startup
- `theme.*` : all `theme` arguments are meant to set default UI colors

**Argument used by our package: (add `--` after streamlit arguments)**

- `verba_port` : the port on which the verba is running (eg `8000`)
- `verba_base_url`: the root url of verba API (topically : `http://localhost`)
- `chunk_size`: (optional) the default size of chunks (can me changed in the app)

Here is an example of the full command (add env variable in `.env` file or export them):

```bash
streamlit run streamlit_rag/app.py --server.port $STREAMLIT_PORT --server.baseUrlPath "/${URL_PREFIX}/" --server.headless true --theme.base dark --theme.primaryColor "4db8a7" -- --verba_port $VERBA_PORT --verba_base_url $BASE_VERBA_API_URL --chunk_size $CHUNK_SIZE
```
