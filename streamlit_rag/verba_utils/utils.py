import logging
import os
import pathlib
import shelve
from typing import Dict, List, Tuple

import streamlit as st
from pydantic import ValidationError
from verba_utils.api_client import APIClient, test_api_connection
from verba_utils.payloads import (
    CachedResponse,
    ConversationItem,
    DocumentSearchQueryResponsePayload,
    GeneratePayload,
    GenerateResponsePayload,
    QueryResponsePayload,
    SearchQueryResponsePayload,
)

log = logging.getLogger(__name__)


def setup_logging(
    logging_level=logging.INFO,
    log_format: str = "[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
):
    """
    Simple function to set up proper python logging
    :param logging_level: Value in [logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG]
    :param log_format: str by default -> "[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s"
    :return: nothing
    """
    logging.basicConfig(level=logging_level, format=log_format)


def write_centered_text(text: str):
    st.markdown(
        f"""<div style=\"text-align: justify;\">{text}</div>""",
        unsafe_allow_html=True,
    )
    st.write("\n")


def create_conversation_items(
    session_state_messages: List[Dict],
) -> List[ConversationItem]:
    result = []
    for element in session_state_messages:
        if "typewriter" in element:
            try:
                result.append(ConversationItem(**element))
            except ValidationError as e:
                log.warning(
                    f"Impossible to convert this message as ConversationItem : {element}, details : {e}"
                )
    return result


def generate_answer(
    prompt: str,
    api_client: APIClient,
    conversation: List[ConversationItem] = [],
    min_nb_words: int = None,
    max_nb_words: int = None,
    return_documents: bool = False,
) -> str | Tuple[str, List]:
    """
    Generate answers to a list of questions. Uses the previously defined query_verba
    :param prompt: str
    :param api_client: APIClient
    :param conversation: List[ConversationItem] (use create_conversation_items() to create it).
                         You cant leave it empty if you don't want to use this feature.
    :param min_nb_words: int
    :param max_nb_words: int
    :param return_documents: bool default False. If true returns (text_response, documents_list)
    :returns: str | Tuple(str, List)
    """

    if max_nb_words is None and min_nb_words is not None:
        max_nb_words = min_nb_words * 2
    if min_nb_words is None and max_nb_words is not None:
        min_nb_words = max_nb_words // 2

    if min_nb_words is not None:  # so max_nb_words is not None either
        question_appendix = f" Please provide an elaborated answer in {min_nb_words} to {max_nb_words} words."
    else:
        question_appendix = ""

    elaborated_question = (str(prompt) + str(question_appendix)).encode("utf-8")
    log.info(f"Cleaned user query : {elaborated_question}")

    if test_api_connection(api_client):
        document_query_response = api_client.query(elaborated_question)
        if (
            document_query_response.system is not None
        ):  # Error when retrieving documents (Verba side)
            log.warning(
                f'Something went wrong when retrieving documents (verba side) : "{document_query_response.system}"'
            )
            response = GenerateResponsePayload(system=document_query_response.system)
        else:
            response = api_client.generate(
                GeneratePayload(
                    query=prompt,
                    context=document_query_response.context,
                    conversation=conversation,
                    # conversation=[],
                )
            )
            if isinstance(response.system, CachedResponse):
                response.system = response.system.message
    else:
        log.error(
            f"Verba API not available {api_client.build_url(api_client.api_routes.health)}, query not submitted"
        )
        response = GenerateResponsePayload(system="Verba API not available")

    if return_documents:
        return response.system, document_query_response.documents
    else:
        return response.system


def display_centered_image(
    image,
    caption=None,
    width=None,
    use_column_width=None,
    clamp=False,
    channels="RGB",
    output_format="auto",
):
    if isinstance(image, pathlib.PosixPath):
        image = str(image)
    # trick to center the image (make 3 columns and display the image in the middle column which is big)
    with st.columns([0.1, 0.98, 0.1])[1]:
        st.image(
            image,
            caption=caption,
            width=width,
            use_column_width=use_column_width,
            clamp=clamp,
            channels=channels,
            output_format=output_format,
        )


def append_documents_in_session_manager(prompt: str, documents: List[Dict]):
    """Append retrieved document in streamlit session_manager
    :param str prompt:
    :param List[Dict] documents:
    """
    if not "retrieved_documents" in st.session_state:
        # init empty list
        st.session_state["retrieved_documents"] = []

    st.session_state["retrieved_documents"].append(
        {"prompt": prompt, "documents": documents}
    )


def get_prompt_history() -> List[str]:
    """Get a list of sent prompts (last one being on top)

    :return List[str]:
    """
    if not "retrieved_documents" in st.session_state:
        return []
    else:
        return [e["prompt"] for e in reversed(st.session_state["retrieved_documents"])]


def get_retrieved_documents_from_prompt(prompt: str) -> List[Dict]:
    """Get the documents retrieved to generate answer to the given prompt
    :param str prompt:
    :return List[Dict]:
    """
    for e in reversed(st.session_state["retrieved_documents"]):
        if e["prompt"] == prompt:
            return e["documents"]
    return []


def doc_id_from_filename(
    filename: str, search_query_response: SearchQueryResponsePayload
) -> str | None:
    """Returns doc id from a given filename (that must be in the provided search_query_response)
    :param str filename:
    :param SearchQueryResponsePayload search_query_response:
    :return str | None: doc id if document found else None
    """
    for e in dict(search_query_response).get("documents", []):
        if e.doc_name == filename:
            return e.additional.id
    return None


def get_ordered_all_filenames(
    documents: List[DocumentSearchQueryResponsePayload],
) -> List[str]:
    """Get all filenames from a SearchQueryResponsePayload alphabetically sorted
    :param SearchQueryResponsePayload search_query_response:
    :return List[str]:
    """
    return sorted([e.doc_name for e in documents])


def store_chatbot_title(title: str):
    """This stores in shelve the custom title set by the user

    :param str title:
    """
    weaviate_tenant = os.getenv("WEAVIATE_TENANT", default="default_tenant")
    log.info(f"Storing new chatbot title (tenant {weaviate_tenant}) : {title}")

    with shelve.open(f"shelve/key_cache_{weaviate_tenant}") as db:
        db["title"] = title


def get_chatbot_title(default_name: str = "Worldline MS Chatbot") -> str:
    """This gets the stored title

    :param str default_name:title to set if nothing is already stored defaults to "Worldline MS Chatbot"
    :return str:
    """
    weaviate_tenant = os.getenv("WEAVIATE_TENANT", default="default_tenant")
    with shelve.open(f"shelve/key_cache_{weaviate_tenant}") as db:
        key = f"title"
        if key in db:
            return db[key]
        else:
            log.info(
                f'No custom chatbot name found for tenant : {weaviate_tenant}, using the default title "{default_name}"'
            )
            return default_name


def reset_chatbot_title():
    """This removes the custom title stored"""
    weaviate_tenant = os.getenv("WEAVIATE_TENANT", default="default_tenant")
    log.info(f"Resetting chatbot title (tenant {weaviate_tenant})")

    with shelve.open("key_cache") as db:
        key = f"{weaviate_tenant}_title"
        if key in db:
            del db[key]
        else:
            log.info(f"{weaviate_tenant} is not in the shelve database.")
