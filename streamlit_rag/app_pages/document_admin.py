import base64
import logging
import os
import pathlib
from typing import List

import streamlit as st
from verba_utils.api_client import APIClient, test_api_connection
from verba_utils.payloads import ChunkerEnum, LoadPayload
from verba_utils.utils import (
    capitalize_first_letter,
    get_chunk_size,
    get_doc_id_from_filename,
    get_ordered_all_filenames,
)

log = logging.getLogger(__name__)

CHUNKER_DESCRIPTION = {
    ChunkerEnum.WORDCHUNKER.value: "Chunk documents by words.",
    ChunkerEnum.TOKENCHUNKER.value: "Chunk documents by tokens powered by [`tiktoken`](https://pypi.org/project/tiktoken/).",
}

DEFAULT_DOC_CATEG = ["Documentation", "Mail", "Tutorial", "Video transcription"]

BASE_ST_DIR = pathlib.Path(os.path.dirname(__file__)).parent
CHUNK_SIZE = get_chunk_size()


def delete_documents(client: APIClient, docs_to_delete_id: List, docs_to_delete: List):
    """Delete the given documents one by one and display a progress bar
    :param client APIClient: (initialized and within a context manager)
    :param docs_to_delete_id List: list of uuid
    :param docs_to_delete List: list of filenames (same index as docs_to_delete_id)
    :return nothing
    """
    nb_docs = len(docs_to_delete_id)

    progress_bar = st.progress(
        0,
        text=f"Sending delete request{'s' if nb_docs > 1 else ''}...",
    )

    for i, (doc_id, doc_name) in enumerate(zip(docs_to_delete_id, docs_to_delete)):
        progress_percent = (i + 1) / nb_docs
        progress_bar.progress(
            progress_percent,
            text=f"Deleting `{doc_name}` ({i+1}/{nb_docs})",
        )

        if client.delete_document(doc_id):  # delete ok
            st.info(f"✅ {doc_name} successfully deleted")
        else:  # delete failed
            st.warning(f"🚨 Something went wrong when trying to delete {doc_name}")

    progress_bar.progress(
        1.0, text=f"Delete quer{'ies' if nb_docs > 1 else 'y'} finished"
    )


st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded",
    page_title="MS RAG Documents",
    page_icon=str(BASE_ST_DIR / "assets/WL_icon.png"),
)


if (not "VERBA_PORT" in os.environ) or (not "VERBA_BASE_URL" in os.environ):
    st.warning(
        '"VERBA_PORT" or "VERBA_BASE_URL" not found in env variable. To solve this, good to Home page and reload the page.'
    )
    st.stop()
else:
    with APIClient() as client:
        is_verba_responding = test_api_connection(client)


if not is_verba_responding["is_ok"]:  # verba api not responding
    st.title("📕 Document administration 🔴")
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

else:  # verba api connected
    st.title("📕 Document administration 🟢")

    # define 3 document sections
    inspect_tab, insert_tab, delete_tab = st.tabs(
        [
            "View uploaded documents",
            "Upload new documents",
            "Remove uploaded documents",
        ]
    )

    with inspect_tab, APIClient() as client:
        doc_list, doc_preview = st.columns([0.3, 0.7])

        with doc_list:
            # display all found document as an ordered radio list
            all_documents = client.get_all_documents()
            filtered_documents = all_documents.documents

            if len(filtered_documents) > 0:
                st.subheader("Search filters")
                if st.button("🔄 Refresh list", type="primary"):
                    # when the button is clicked, the page will refresh by itself :)
                    log.debug("Refresh page")

                selected_doc_types = st.multiselect(
                    "Select the document category",
                    all_documents.doc_types,
                    placeholder="Choose one or many types in the list",
                )

                if len(selected_doc_types) > 0:
                    filtered_documents = [
                        doc
                        for doc in filtered_documents
                        if doc.doc_type in selected_doc_types
                    ]

                chosen_doc = st.selectbox(
                    f"Select a document: (total : {len(filtered_documents)})",
                    get_ordered_all_filenames(filtered_documents),
                    index=None if len(filtered_documents) > 1 else 0,
                    placeholder="Type part of filename or browse in the list",
                )

            else:
                chosen_doc = None
                if st.button("🔄 Refresh list", type="primary"):
                    # when the button is clicked, the page will refresh by itself :)
                    log.debug("Refresh page")
                st.write("No document found")

        with doc_preview:  # display select document text content
            if chosen_doc is not None:
                document_id = get_doc_id_from_filename(
                    chosen_doc,
                    all_documents.documents,
                )
                doc_info = client.get_document(document_id)

                st.subheader(
                    f"{chosen_doc} :red[[{doc_info.document.properties.doc_type}]]"
                )
                st.text_area(
                    label=f"Upload date: {doc_info.document.properties.timestamp} - Document id : {document_id} - Chunks count : {doc_info.document.properties.chunk_count}",
                    value=doc_info.document.properties.text,
                    height=600,
                )

    with insert_tab, APIClient() as client:
        st.subheader("Document uploader")

        with st.expander("Upload parameters", expanded=False):
            st.info(
                "If you don't know what you are doing, please don't change the settings"
            )

            col0, col1 = st.columns(2)
            chuck_size = col0.slider(
                "Select chunk size",
                min_value=50,
                max_value=500,
                value=CHUNK_SIZE,
                step=50,
            )

            chunker = col1.selectbox(
                "Select a chunker",
                [e.value for e in ChunkerEnum],
                index=0,
            )

            col1.markdown(f"**{chunker}**: {CHUNKER_DESCRIPTION[chunker]}")

        # Initialize session state if not present
        if "doc_types" not in st.session_state:
            all_documents = client.get_all_documents()
            st.session_state["doc_types"] = sorted(
                set(all_documents.doc_types + DEFAULT_DOC_CATEG)
            )

        col0, col1 = st.columns([0.5, 0.5])

        try:
            default_index = st.session_state["doc_types"].index(DEFAULT_DOC_CATEG[0])
        except ValueError:
            default_index = None

        new_doc_type = capitalize_first_letter(col1.text_input("Add a new category"))

        if new_doc_type and new_doc_type not in st.session_state["doc_types"]:
            st.session_state["doc_types"].append(new_doc_type)
            st.session_state["doc_types"] = sorted(set(st.session_state["doc_types"]))

        # Document category selection
        doc_type = col0.selectbox(
            "Choose the document category",
            st.session_state["doc_types"],
            index=default_index,
        )

        with st.form("document_form", clear_on_submit=True):
            uploaded_files = st.file_uploader(
                label="Upload your .txt or .md documents",
                type=["txt", "md"],
                accept_multiple_files=True,
            )

            # Submit button
            if st.form_submit_button("Submit documents", type="primary"):
                if uploaded_files:
                    already_uploaded_documents = client.get_all_documents().documents
                    already_uploaded_filenames = get_ordered_all_filenames(
                        already_uploaded_documents
                    )

                    # Initialize payload
                    loadPayload = LoadPayload(
                        reader="SimpleReader",
                        chunker=chunker,
                        embedder="ADAEmbedder",
                        document_type=doc_type,
                        chunkUnits=chuck_size,
                        chunkOverlap=50,
                        fileBytes=[],
                        fileNames=[],
                    )

                    for file in uploaded_files:
                        # build rest of the payload
                        if file.name in already_uploaded_filenames:
                            # removing already existing documents
                            st.warning(
                                f"`{file.name}` is already in the database, it will be overwritten",
                                icon="ℹ️",
                            )
                            doc_id_to_delete = get_doc_id_from_filename(
                                file.name, already_uploaded_documents
                            )
                            if doc_id_to_delete:
                                client.delete_document(doc_id_to_delete)

                        encoded_document = base64.b64encode(file.getvalue()).decode(
                            "utf-8"
                        )
                        loadPayload.fileBytes.append(encoded_document)
                        loadPayload.fileNames.append(file.name)

                    file_names_str = "` `".join(loadPayload.fileNames)
                    with st.spinner(
                        f"Uploading `{file_names_str}`. Please wait. Expect about 1 second per KB of text."
                    ):
                        response = client.load_data(
                            LoadPayload.model_validate(loadPayload)
                        )
                        if str(response.status) == "200":
                            st.info(f"✅ Documents successfully uploaded")
                        else:
                            st.error(
                                f'Something went wrong when submitting documents {loadPayload.fileNames} http response  [{response.status}] -> "{response.status_msg}"'
                            )
                            st.info(
                                "Please check the error message above. If it is an Error 429 it means that the API is overloaded. Please try again later. If it is an encoding related error you might try to upload files one by one to check which one is causing the error."
                            )
                            st.title("Debug info (share it with maintainers):")
                            with st.expander("Sent POST payload :"):
                                st.write(loadPayload)
                            with st.expander("Received response :"):
                                st.write(response)
                else:
                    st.warning(
                        "No document uploaded, please upload your document before submitting"
                    )

    with delete_tab, APIClient() as client:
        all_documents = client.get_all_documents()
        if st.button("🔄 Refresh", type="primary"):
            # when the button is clicked, the page will refresh by itself :)
            log.debug("Refresh page")

        if len(all_documents.documents) > 0:  # uploaded documents exist
            st.subheader("Delete documents", divider="red")

            docs_to_delete = st.multiselect(
                "Select the documents you want to delete",
                get_ordered_all_filenames(all_documents.documents),
                placeholder="Choose one or many documents in the list",
            )

            if docs_to_delete:  # if user selected at least 1 document
                show_preview = st.toggle("Show preview", value=True)
                nb_docs = len(docs_to_delete)

                docs_to_delete_id = [
                    get_doc_id_from_filename(
                        e,
                        all_documents.documents,
                    )
                    for e in docs_to_delete
                ]

                for doc in docs_to_delete:
                    doc_to_delete_id = get_doc_id_from_filename(
                        doc,
                        all_documents.documents,
                    )
                    doc_to_delete_text = client.get_document(
                        doc_to_delete_id
                    ).document.properties.text

                    with st.expander(
                        f"Preview of `{doc}`",
                        expanded=show_preview,
                    ):
                        st.text_area(
                            label=doc,
                            value=doc_to_delete_text,
                            height=300,
                            label_visibility="collapsed",
                        )
                if st.button(
                    f"🗑️ Delete {nb_docs} document{'s' if nb_docs> 1 else ''} (irreversible)",
                ):
                    delete_documents(client, docs_to_delete_id, docs_to_delete)

            st.subheader(":red[Danger zone]", divider="red")
            col0, col1 = st.columns(2)
            if col0.checkbox(":red[Delete all documents]") and col1.button(
                f"I am sure I want to delete all documents (total: {len(all_documents.documents)})",
                type="primary",
            ):
                all_docs_id = [
                    get_doc_id_from_filename(
                        e.doc_name,
                        all_documents.documents,
                    )
                    for e in all_documents.documents
                ]
                all_docs_name = get_ordered_all_filenames(all_documents.documents)
                delete_documents(client, all_docs_id, all_docs_name)

        else:  # no documents uploaded
            st.subheader("No document uploaded yet")
