import os
import pathlib

import click
import streamlit as st
from app_pages import chatbot
from st_pages import Page, show_pages
from verba_utils.utils import get_chatbot_title, setup_logging

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

    chatbot.chatbot()


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

    main()
