import logging
import os
import pathlib
from typing import Dict

import streamlit as st
from verba_utils.api_client import APIClient, test_api_connection
from verba_utils.payloads import DocumentChunk
from verba_utils.utils import get_prompt_history, get_retrieved_chunks_from_prompt

BASE_ST_DIR = pathlib.Path(os.path.dirname(__file__)).parent
NUM_COLUMNS = 3

log = logging.getLogger(__name__)


st.set_page_config(
    initial_sidebar_state="expanded",
    layout="centered",
    page_title="Source documents",
    page_icon=str(BASE_ST_DIR / "assets/WL_icon.png"),
)

if (not "VERBA_PORT" in os.environ) or (not "VERBA_BASE_URL" in os.environ):
    st.warning(
        '"VERBA_PORT" or "VERBA_BASE_URL" not found in env variable. To solve this, good to Home page and reload the page.'
    )
    st.stop()
else:
    api_client = APIClient()

is_verba_responding = test_api_connection(api_client)

title = "📁 Source documents"

if not is_verba_responding["is_ok"]:  # verba api not responding
    st.title(f"{title} 🔴")
    if "upload a key using /api/set_openai_key" in is_verba_responding["error_details"]:
        st.error(
            f"Your openapi key is not set yet. Go set it in **Administration** page",
            icon="🚨",
        )

    else:
        st.error(
            f"Connection to verba backend failed -> details : {is_verba_responding['error_details']}",
            icon="🚨",
        )
    if st.button("🔄 Try again", type="primary"):
        # when the button is clicked, the page will refresh by itself :)
        log.debug("Refresh page")

else:
    # verba api connected
    st.title(f"{title} 🟢")

    if not "retrieved_documents" in st.session_state:
        st.write(
            "Here, you will find the source documents used to generate the answer for each of your prompts."
        )
    else:
        chosen_prompt = st.selectbox(
            "Select the prompt for which you want to see the source documents",
            get_prompt_history(),
            index=0,
        )
        retrieved_documents = get_retrieved_chunks_from_prompt(chosen_prompt)

        # Empty container to hold button callbacks
        button_callbacks: Dict[str, DocumentChunk] = {}

        # Display the grid of buttons per retrieved_documents
        for i, element in enumerate(retrieved_documents):
            # This will create a new row after every num_columns items
            if i % NUM_COLUMNS == 0:
                cols = st.columns(NUM_COLUMNS)  # Create new columns

            # Define the button and its callback within the corresponding column
            with cols[i % NUM_COLUMNS]:  # Selects the correct column
                # Unique key for each button (you can also use other methods to generate a unique key)
                button_key = f"button_{i}"

                # Create the button and check if it's clicked
                if st.button(
                    f"{element.doc_name} [Score {element.score:.2f}]", key=button_key
                ):
                    # Store or process the click event
                    button_callbacks[button_key] = element

        for key, document_chunk in button_callbacks.items():
            with st.expander(
                f":green[Document : {document_chunk.doc_name} - Chunk {document_chunk.chunk_id}]",
                expanded=True,
            ):
                with st.container():
                    st.markdown(document_chunk.text)
