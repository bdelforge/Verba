import logging
import os
import pathlib
import shelve

import streamlit as st
from verba_utils.api_client import APIClient, test_api_connection
from verba_utils.utils import (
    get_chatbot_title,
    reset_chatbot_title,
    store_chatbot_title,
)

BASE_ST_DIR = pathlib.Path(os.path.dirname(__file__)).parent

log = logging.getLogger(__name__)


st.set_page_config(
    layout="centered",
    initial_sidebar_state="expanded",
    page_title="Administration",
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

if not is_verba_responding["is_ok"] and not (
    "upload a key using /api/set_openai_key" in is_verba_responding["error_details"]
):  # verba api not responding
    st.title("⚙️ Administration 🔴")
    if "upload a key using /api/set_openai_key" in is_verba_responding["error_details"]:
        pass  # normal not to have api keys at first on this page

    else:
        st.error(
            f"Connection to verba backend failed -> details : {is_verba_responding['error_details']}",
            icon="🚨",
        )
    if st.button("🔄 Try again", type="primary"):
        # when the button is clicked, the page will refresh by itself :)
        log.debug("Refresh page")

else:
    st.title("⚙️ Administration 🟢")
    st.info(
        """
        Please do not alter any settings if you are not sure what you are doing. 
        Unwanted changes/actions can disrupt your chatbot instance.
        """,
        icon="⚠️",
    )

    st.subheader("Open AI API key", divider="blue")
    key_preview = api_client.get_openai_key_preview()
    if len(key_preview) > 0:
        st.markdown("#### Current uploaded key :")
        col0, col1, col2, col3, col4 = st.columns([0.17, 0.17, 0.32, 0.17, 0.17])
        with col0:
            if st.button("🔄 Refresh", type="primary"):
                # when the button is clicked, the page will refresh by itself :)
                log.debug("Refresh page")

        with col1:
            show = st.toggle("Show API key preview")

        with col2:
            if show:
                st.markdown(f"`{key_preview}`")
            else:
                st.markdown(f"`{'*' * len(key_preview)}`")

        with col3:
            if st.button("🧪Test API key"):
                with st.spinner("Testing your API key..."):
                    res = api_client.test_openai_api_key()
                if res["status"] == "200":
                    st.success("✅ API key is working")
                else:
                    st.error(
                        f"API key is not working",
                        icon="🚨",
                    )
                    with st.expander("Details error : "):
                        st.write(res["status_msg"])

        with col4:
            if st.checkbox("🗑️ Delete API key"):
                if st.button("⚠️Confirm (irreversible) ⚠️", type="primary"):
                    with st.spinner("Removing your API key..."):
                        success = api_client.unset_openai_key()
                        if success:
                            st.info("Key successfully removed")
                        else:
                            st.error("Something went wrong when deleting your key")

    else:
        st.header("No Open AI API key uploaded yet")
        col0, col1, col2, col3, col4 = st.columns([0.17, 0.17, 0.32, 0.17, 0.17])
        with col0:
            if st.button("🔄 Refresh", type="primary"):
                # when the button is clicked, the page will refresh by itself :)
                log.debug("Refresh page")
    st.markdown("#### Enter your new API key (it overwrites the previous one):")
    api_key = st.text_input("API Key", type="password")

    if st.button("Submit"):
        if api_key:
            with st.spinner("Uploading your secret api key..."):
                res = api_client.set_openai_key(api_key=api_key)
                if res.status == "200":
                    st.success(
                        "✅ API key saved successfully. You can refresh the list and test it!"
                    )
                else:
                    st.error(
                        f"Connection to verba backend failed -> details : {res.status_msg}",
                        icon="🚨",
                    )
        else:
            st.warning("Please enter a valid API key.")
    st.subheader("Change Chatbot title", divider="blue")
    with st.form("chatbot_title", clear_on_submit=True):
        title = st.text_input("New chatbot welcome page title:")
        col1, _, col3 = st.columns([0.20, 0.7, 0.20])
        with col1:
            submit = st.form_submit_button("Submit new title", type="primary")
        with col3:
            remove = st.form_submit_button("Set title to default")

        if (title != "") and submit:  # new title and click on submit
            store_chatbot_title(title)
            st.success(f"✅ Chatbot title (`{get_chatbot_title()}`) successfully saved")

        if title == "" and submit:  # click on submit with empty title
            st.warning("⚠️ Please enter a valid title in the text area")

        if remove:  # click on remove
            reset_chatbot_title()
            st.success(
                f"✅ Chatbot title successfully set to default (`{get_chatbot_title()}`)"
            )
