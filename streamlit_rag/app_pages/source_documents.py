import logging
import os
import pathlib

import streamlit as st
from verba_utils.api_client import APIClient, test_api_connection
from verba_utils.utils import get_prompt_history, get_retrieved_documents_from_prompt

BASE_ST_DIR = pathlib.Path(os.path.dirname(__file__)).parent
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
        retrieved_documents = get_retrieved_documents_from_prompt(chosen_prompt)
        st.divider()
        for document in retrieved_documents:
            st.text_area(
                label=f"Document : {document.get('doc_name')} (chunk {document.get('chunk_id')}), retrieval score {document.get('_additional').get('score')}) ",
                value=f"{document.get('text')}",
                height=230,
            )
