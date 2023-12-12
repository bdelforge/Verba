import logging
import os
import pathlib

import click
import streamlit as st
from st_pages import Page, show_pages
from verba_utils.api_client import APIClient, test_api_connection
from verba_utils.utils import (
    append_documents_in_session_manager,
    create_conversation_items,
    generate_answer,
    get_chatbot_title,
    setup_logging,
)

BASE_ST_DIR = pathlib.Path(os.path.dirname(__file__))


@click.command()
@click.option(
    "--verba_port",
    "-vp",
    type=str,
    help="Verba backend api port, usually in our case 8000 + tenant number ",
)
@click.option(
    "--verba_base_url",
    type=str,
    help="Verba base api url usually in our case http://localhost)",
)
@click.option("--chunk_size", default=300, type=int, help="Size of the chunk")
def main(verba_port, verba_base_url, chunk_size):
    if not (verba_port and verba_base_url):
        st.error(
            f"""
            Streamlit app is not properly started, make sure to provide the following cli arguments 
            `verba_port` (current value : {verba_port}) and 
            `verba_base_url` (current value :  {verba_base_url}). 
            Hint : you may need to look at https://docs.streamlit.io/library/get-started/main-concepts
            """
        )

    os.environ["VERBA_PORT"] = verba_port
    os.environ["VERBA_BASE_URL"] = verba_base_url
    os.environ["CHUNK_SIZE"] = str(chunk_size)

    log = logging.getLogger(__name__)

    if (not "VERBA_PORT" in os.environ) or (not "VERBA_BASE_URL" in os.environ):
        st.warning(
            '"VERBA_PORT" or "VERBA_BASE_URL" not found in env variable. To solve this, good to Home page and reload the page.'
        )
        st.stop()
    else:
        api_client = APIClient()

    is_verba_responding = test_api_connection(api_client)

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

        with st.expander("session_state"):
            st.write(st.session_state)

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
                        response, documents = generate_answer(
                            prompt,
                            api_client,
                            conversation=conversation,
                            max_nb_words=max_worlds_answers,
                            return_documents=True,
                        )
                        st.markdown(response)
                        with st.expander("conversation"):
                            st.write(conversation)
                        append_documents_in_session_manager(prompt, documents)
                    if response:
                        message = {
                            "type": "system",
                            "content": response,
                            "typewriter": False,
                        }
                        st.session_state.messages.append(message)


if __name__ == "__main__":
    setup_logging()

    try:
        TITLE = get_chatbot_title()
    except:  # Should never happen but I don't want the app to crash for a title
        TITLE = "Worldline MS Chatbot"

    st.set_page_config(
        initial_sidebar_state="expanded",
        layout="centered",
        page_title=TITLE,
        page_icon=str(BASE_ST_DIR / "assets/WL_icon.png"),
    )

    show_pages(
        [
            Page(BASE_ST_DIR / "app.py", "Chatbot"),
            Page(
                BASE_ST_DIR / "app_pages/source_documents.py",
                "Source documents",
            ),
            Page(
                BASE_ST_DIR / "app_pages/document_admin.py",
                "Document administration",
            ),
            Page(BASE_ST_DIR / "app_pages/admin.py", "Administration"),
        ]
    )

    st.sidebar.header("Config")
    max_worlds_answers = st.sidebar.slider(
        "Select maximum words in answer:",
        min_value=40,
        max_value=500,
        value=100,
        step=20,
    )
    main()
