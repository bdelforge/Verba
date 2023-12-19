import logging
import os
import shelve
from typing import Dict, List, Tuple

import streamlit as st
from pydantic import ValidationError
from verba_utils.api_client import APIClient, test_api_connection
from verba_utils.payloads import (
    CachedResponse,
    ConversationItem,
    DocumentChunk,
    DocumentSearchQueryResponsePayload,
    GeneratePayload,
    GenerateResponsePayload,
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


def create_conversation_items(
    session_state_messages: List[Dict],
) -> List[ConversationItem]:
    """Creates a list of ConversationItem objects from a list of dictionaries representing messages (usually st.session_state["messages"]).
    If the last message in the list contains the "typewriter" key with the value set to `False`, that message is ignored (last user prompt).
    Otherwise, each message that includes the "typewriter" key is attempted to be converted into a ConversationItem object.

    :param session_state_messages: List[Dict] -> a list of message dictionaries to be converted into ConversationItems
    :returns: List[ConversationItem] excluding the last message if it has "typewriter": False
    """

    conversation_items = []

    # Determine the range for the iteration based on the last element condition (ignore last user prompt)
    if session_state_messages and session_state_messages[-1].get("typewriter") is True:
        messages_to_process = session_state_messages[:-1]
    else:
        messages_to_process = session_state_messages

    for message in messages_to_process:
        if "typewriter" in message:
            try:
                conversation_items.append(ConversationItem(**message))
            except ValidationError as e:
                log.warn(
                    f"Impossible to convert this message as ConversationItem: {message}, details: {e}"
                )

    return conversation_items


def test_api_key(client: APIClient):
    res = client.test_openai_api_key()

    if res["status"] == "200":
        st.success("✅ API key is working")
    else:
        st.error(
            f"API key is not working",
            icon="🚨",
        )
        with st.expander("Error details:"):
            st.markdown(res["status_msg"])


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
    :param conversation: List[ConversationItem] (use utils.create_conversation_items to create it).
    :param min_nb_words: int
    :param max_nb_words: int
    :param return_documents: bool default False. If true returns (text_response, documents_list)
    :returns: str | Tuple(str, List)
    """

    # Apply the logic for setting min/max words depending on the provided values
    if max_nb_words is None and min_nb_words is not None:
        max_nb_words = min_nb_words * 2
    elif min_nb_words is None and max_nb_words is not None:
        min_nb_words = max_nb_words // 2

    # Add the appendix only if both min_nb_words and max_nb_words have values
    if min_nb_words is not None and max_nb_words is not None:
        question_appendix = f" Please provide an elaborated answer in {min_nb_words} to {max_nb_words} words."
    else:
        question_appendix = ""

    elaborated_question = (str(prompt) + str(question_appendix)).encode("utf-8")
    log.info(f"Cleaned user query : {elaborated_question}")

    if test_api_connection(api_client):
        query_response = api_client.query(elaborated_question)
        if (
            query_response.system is not None
        ):  # Error when retrieving documents (Verba side)
            log.warning(
                f'Something went wrong when retrieving documents (verba side) : "{query_response.system}"'
            )
            response = GenerateResponsePayload(system=query_response.system)
        else:  # query went fine, now generate LLM response
            response = api_client.generate(
                GeneratePayload(
                    query=prompt,
                    context=query_response.context,
                    conversation=conversation,
                )
            )
            if isinstance(response.system, CachedResponse):
                # Verba returns a different payload format when the answer is from cache...
                response.system = response.system.message
    else:
        log.error(
            f"Verba API not available {api_client._build_url(api_client.api_routes.health)}, query not submitted"
        )
        response = GenerateResponsePayload(system="Verba API not available")

    if return_documents:
        return response.system, query_response.documents
    else:
        return response.system


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


def get_retrieved_chunks_from_prompt(prompt: str) -> List[DocumentChunk]:
    """Get the documents retrieved to generate answer to the given prompt
    They will be sorted by decreasing score
    :param str prompt:
    :return List[DocumentChunk]:
    """
    for e in reversed(st.session_state.get("retrieved_documents", [])):
        if e["prompt"] == prompt:
            return sorted(e["documents"], key=lambda chunk: chunk.score, reverse=True)
    return []


def get_doc_id_from_filename(
    filename: str, documents: List[DocumentSearchQueryResponsePayload]
) -> str | None:
    """Returns doc id from a given filename (that must be in the provided search_query_response)
    :param str filename:
    :param SearchQueryResponsePayload search_query_response:
    :return str | None: doc id if document is found else None
    """
    return next(
        (e.additional.id for e in documents if e.doc_name == filename),
        None,
    )


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

    with shelve.open(f"shelve/key_cache_{weaviate_tenant}") as db:
        key = f"title"
        if key in db:
            del db[key]
        else:
            log.info(f"{weaviate_tenant} is not in the shelve database.")


def get_chunk_size(default: int = 300) -> int:
    try:
        return int(os.environ.get("CHUNK_SIZE", default))
    except ValueError:
        log.warn(
            f"Cannot cast 'CHUNK_SIZE' to int, value : {os.environ.get('CHUNK_SIZE', default)}. Setting it to default {default}"
        )
        return default


def capitalize_first_letter(input_string: str) -> str | None:
    if not input_string:
        return input_string
    # Split the string into words, capitalize the first letter of the first word,
    # and make sure the rest of the words are in lowercase.
    words = input_string.split()
    # Capitalize the first word and lowercase the rest of the words
    words = [words[0].capitalize()] + [word.lower() for word in words[1:]]
    # Join the words back into a single string
    return " ".join(words)
