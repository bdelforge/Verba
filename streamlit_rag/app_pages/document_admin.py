import base64
import logging
import os
import pathlib

import streamlit as st
from verba_utils.api_client import APIClient, test_api_connection
from verba_utils.payloads import ChunkerEnum, LoadPayload
from verba_utils.utils import get_doc_id_from_filename, get_ordered_all_filenames

log = logging.getLogger(__name__)

CHUNKER_DESCRIPTION = {
    ChunkerEnum.WORDCHUNKER.value: "Chunk documents by words.",
    ChunkerEnum.TOKENCHUNKER.value: "Chunk documents by tokens powered by tiktoken.",
}


BASE_ST_DIR = pathlib.Path(os.path.dirname(__file__)).parent

try:
    CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", 300))
except ValueError:
    CHUNK_SIZE = 300
    log.warn(
        f"Can't cast os.environ.get('CHUNK_SIZE', 300) to int, value : {os.environ.get('CHUNK_SIZE', 300)}. Setting it to default {CHUNK_SIZE}"
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
    api_client = APIClient()

is_verba_responding = test_api_connection(api_client)


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

else:
    # verba api connected
    st.title("📕 Document administration 🟢")

    # define 3 document sections
    inspect_tab, insert_tab, delete_tab = st.tabs(
        [
            "Inspect uploaded documents",
            "Upload new documents",
            "Remove uploaded documents",
        ]
    )

    with inspect_tab:
        doc_list, doc_preview = st.columns([0.3, 0.7])

        with doc_list:  # display all found document as an ordered radio list
            all_documents = api_client.get_all_documents()
            filtered_documents = all_documents.documents

            if len(filtered_documents) > 0:
                st.subheader("Search filters")
                selected_doc_types = st.multiselect(
                    "Select the document type",
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

                if st.button("🔄 Refresh list", type="primary"):
                    # when the button is clicked, the page will refresh by itself :)
                    log.debug("Refresh page")

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
                doc_info = api_client.get_document(document_id)

                st.subheader(
                    f"{chosen_doc} :red[[{doc_info.document.properties.doc_type}]]"
                )
                st.text_area(
                    label=f"Upload date: {doc_info.document.properties.timestamp} - Document id : {document_id} - Chunks count : {doc_info.document.properties.chunk_count}",
                    value=doc_info.document.properties.text,
                    height=600,
                )

    with insert_tab:
        st.subheader("Document uploader")

        with st.expander("Upload parameters", expanded=False):
            st.info(
                "Please, if you don't know what you are doing, please don't change the settings"
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

        with st.form("document_form", clear_on_submit=True):
            uploaded_files = st.file_uploader(
                label="Upload your .txt or .md documents",
                type=["txt", "md"],
                accept_multiple_files=True,
            )
            document_type = st.text_input("Kind of documents", value="Documentation")

            # Submit button
            if st.form_submit_button("Submit documents", type="primary"):
                if uploaded_files:
                    already_uploaded_documents = (
                        api_client.get_all_documents().documents
                    )
                    already_uploaded_filenames = get_ordered_all_filenames(
                        already_uploaded_documents
                    )

                    # Initialize payload
                    loadPayload = LoadPayload(
                        reader="SimpleReader",
                        chunker=chunker,
                        embedder="ADAEmbedder",
                        document_type=document_type,
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
                                api_client.delete_document(doc_id_to_delete)

                        encoded_document = base64.b64encode(file.getvalue()).decode(
                            "utf-8"
                        )
                        loadPayload.fileBytes.append(encoded_document)
                        loadPayload.fileNames.append(file.name)

                    file_names_str = "` `".join(loadPayload.fileNames)
                    with st.spinner(
                        f"Uploading `{file_names_str}`. Please wait. Expect about 1 second per KB of text."
                    ):
                        response = api_client.load_data(
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

    with delete_tab:
        all_documents = api_client.get_all_documents()
        if not len(all_documents.documents) > 0:  # no uploaded documents
            st.subheader("No document uploaded yet")
        else:
            st.subheader("Delete documents")
            if st.button("🔄 Refresh", type="primary"):
                # when the button is clicked, the page will refresh by itself :)
                log.debug("Refresh page")
            document_to_delete = st.selectbox(
                "Select the document you want to delete",
                get_ordered_all_filenames(all_documents.documents),
                index=None,
            )

            if document_to_delete:  # if user selected a document
                document_to_delete_id = get_doc_id_from_filename(
                    document_to_delete,
                    all_documents.documents,
                )
                if st.button(
                    "🗑️ Delete document (irreversible)",
                ):
                    with st.spinner("Sending delete request..."):
                        is_document_deleted = api_client.delete_document(
                            document_to_delete_id
                        )
                        if is_document_deleted:  # delete ok
                            st.info(f"✅ {document_to_delete} successfully deleted")
                        else:  # delete failed
                            st.warning(
                                f"🚨 Something went wrong when trying to delete {document_to_delete}"
                            )
            st.subheader(":red[Danger zone]", divider="red")
            col0, col1 = st.columns(2)
            if col0.checkbox(":red[Delete all documents]") and col1.button(
                f"I am sure I want to delete all documents (total: {len(all_documents.documents)})",
                type="primary",
            ):
                with st.spinner("Deleting all your documents..."):
                    for doc in get_ordered_all_filenames(all_documents.documents):
                        curr_doc_to_delete_id = get_doc_id_from_filename(
                            doc,
                            all_documents.documents,
                        )
                        is_document_deleted = api_client.delete_document(
                            curr_doc_to_delete_id
                        )
                        if is_document_deleted:  # delete ok
                            st.info(f"✅ {doc} successfully deleted")
                        else:  # delete failed
                            st.warning(
                                f"🚨 Something went wrong when trying to delete {doc}"
                            )
