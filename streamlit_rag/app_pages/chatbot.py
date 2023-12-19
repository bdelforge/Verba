import logging
import os
import pathlib

import streamlit as st
from verba_utils.api_client import APIClient, test_api_connection
from verba_utils.utils import (
    append_documents_in_session_manager,
    create_conversation_items,
    generate_answer,
    get_chatbot_title,
)

log = logging.getLogger(__name__)


BASE_ST_DIR = pathlib.Path(os.path.dirname(__file__)).parent

try:
    TITLE = get_chatbot_title()
except:  # Should never happen but I don't want the app to crash for a title
    TITLE = "Worldline MS Chatbot"


def chatbot():
    st.sidebar.header("Answers config")
    if st.sidebar.checkbox("Set min/max words in LLM answer"):
        min_worlds_answers, max_worlds_answers = st.sidebar.slider(
            "Select a range of values",
            min_value=50,
            max_value=500,
            value=(50, 100),
            step=50,
        )
    else:
        min_worlds_answers, max_worlds_answers = None, None

    if (not "VERBA_PORT" in os.environ) or (not "VERBA_BASE_URL" in os.environ):
        st.warning(
            '"VERBA_PORT" or "VERBA_BASE_URL" not found in env variable. To solve this, good to Home page and reload the page.'
        )
        st.stop()
    else:
        with APIClient() as client:
            is_verba_responding = test_api_connection(client)

    if not is_verba_responding["is_ok"]:  # verba api not responding
        st.title(f"🤖 {TITLE} 🔴")
        if (
            "upload a key using /api/set_openai_key"
            in is_verba_responding["error_details"]
        ):
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
    else:  # verba api connected
        st.title(f"🤖 {TITLE} 🟢")

        if st.button("Reset conversation", type="primary"):
            # Delete message and document items in session state
            if "messages" in st.session_state:
                del st.session_state["messages"]
            if "retrieved_documents" in st.session_state:
                del st.session_state["retrieved_documents"]

        if "messages" not in st.session_state.keys():
            st.session_state.messages = [
                {
                    "type": "system",
                    "content": "Greetings! I am your chatbot assistant, here to help. If the answers to your questions are in the documents you've uploaded, I can provide them. While you're free to ask in any language, for the best results, I recommend using the language of the uploaded documents.",
                }  # NOTE : I do not define "typewriter" on purpose, I want this message to be ignored when building conversation_items payload
            ]

        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(
                message["type"],
                avatar=str(BASE_ST_DIR / "assets/WL.png")
                if message["type"] == "system"
                else None,
            ):
                st.markdown(message["content"])

        # User-provided prompt
        if prompt := st.chat_input():
            st.session_state.messages.append(
                {"type": "user", "content": prompt, "typewriter": True}
            )
            with st.chat_message("user"):
                st.markdown(prompt)

        # Generate a new response if last message is not from system
        if st.session_state.messages[-1]["type"] != "system":
            with st.chat_message("system", avatar=str(BASE_ST_DIR / "assets/WL.png")):
                with st.spinner("Thinking..."):
                    response, documents = None, None
                    if prompt is not None:
                        conversation = create_conversation_items(
                            st.session_state.get("messages", [])
                        )
                        with APIClient() as client:
                            response, documents = generate_answer(
                                prompt,
                                client,
                                conversation=conversation,
                                max_nb_words=max_worlds_answers,
                                min_nb_words=min_worlds_answers,
                                return_documents=True,
                            )
                        st.markdown(response)
                        append_documents_in_session_manager(prompt, documents)
                    if response:
                        message = {
                            "type": "system",
                            "content": response,
                            "typewriter": False,
                        }
                        st.session_state.messages.append(message)
