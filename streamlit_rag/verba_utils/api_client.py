import logging
from typing import Dict

import requests
from pydantic import Field
from pydantic_core._pydantic_core import ValidationError
from pydantic_settings import BaseSettings
from tenacity import RetryError, retry, stop_after_attempt, wait_exponential
from verba_utils.payloads import (
    APIKeyPayload,
    APIKeyResponsePayload,
    GeneratePayload,
    GenerateResponsePayload,
    GetDocumentPayload,
    GetDocumentResponsePayload,
    LoadPayload,
    LoadResponsePayload,
    QueryPayload,
    QueryResponsePayload,
    SearchQueryPayload,
    SearchQueryResponsePayload,
)

log = logging.getLogger(__name__)


class API_routes(BaseSettings):
    verba_port: str | int = Field(default="8000", env="VERBA_PORT")
    verba_base_url: str = Field(default="http://localhost", env="VERBA_BASE_URL")
    health: str = "health"
    query: str = "query"
    generate: str = "generate"
    get_all_documents: str = "get_all_documents"
    get_document: str = "get_document"
    get_components: str = "get_components"
    load_data: str = "load_data"
    delete_document: str = "delete_document"
    set_openai_key: str = "set_openai_key"
    get_openai_key_preview: str = "get_openai_key_preview"
    unset_openai_key: str = "unset_openai_key"
    test_openai_api_key: str = "test_openai_api_key"

    @property
    def base_api_url(self) -> str:
        return f"{self.verba_base_url}:{self.verba_port}/api"


class APIClient:
    def __init__(self):
        self.api_routes = API_routes()

    def make_request(
        self, method, endpoint, params=None, data=None, json=None
    ) -> requests.Response:
        """Generic method to make any request to the backend

        :param str method: _description_
        :param str endpoint: _description_
        :param params: defaults to None
        :param data: defaults to None
        :param json: defaults to None
        :return _type_:  requests.Response
        """
        headers = {
            "content-type": "application/json",
        }
        url = self.build_url(endpoint)
        log.info(f"Sending {method} request to {url}")
        return requests.request(
            method,
            url,
            params=params,
            json=json,
            data=data,
            headers=headers,
        )

    def build_url(self, endpoint: str) -> str:
        """Helper function to build the endpoint url

        :param str endpoint: one attribute of API_routes
        :return str:
        """
        return f"{self.api_routes.base_api_url}/{endpoint}"

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def health_check(self) -> requests.Response:
        # If this function fails three times in a row,
        # it will stop being retried after approximately 6 seconds
        # (2 seconds for the second attempt + 4 seconds for the third attempt).
        # This is meant to avoid error when verba is starting
        return self.make_request("GET", self.api_routes.health)

    def query(self, data: str) -> QueryResponsePayload:
        response = self.make_request(
            method="POST",
            endpoint=self.api_routes.query,
            json={"query": data.decode("utf-8")},
        )
        if response.status_code == requests.status_codes.codes["ok"]:
            try:
                return QueryResponsePayload.model_validate(response.json())
            except ValidationError as e:
                log.warning(
                    f"Impossible to convert query response as QueryResponsePayload : {response.json()}, details : {e}"
                )
        else:
            log.warning(f"POST query returned code [{response.status_code}]")
        return QueryResponsePayload(
            system="Sorry, something went wrong when proceeding your request"
        )

    def generate(self, generate_payload: GeneratePayload) -> GenerateResponsePayload:
        response = self.make_request(
            method="POST",
            endpoint=self.api_routes.generate,
            json=generate_payload.model_dump(),
        )
        if response.status_code == requests.status_codes.codes["ok"]:
            try:
                return GenerateResponsePayload.model_validate(response.json())
            except ValidationError as e:
                log.warning(
                    f"Impossible to convert /generate response as GenerateResponsePayload : {response.json()}, details : {e}"
                )
        else:
            log.warning(
                f"POST /generate returned code [{response.status_code}] -> details {response.content}"
            )
            return GenerateResponsePayload(
                system=f"Sorry, something went wrong when proceeding your query. \n\nDetails : `{response.content}`"
            )

    def get_all_documents(
        self, query: str = "", doc_type: str = ""
    ) -> SearchQueryResponsePayload:
        response = self.make_request(
            method="POST",
            endpoint=self.api_routes.get_all_documents,
            data=SearchQueryPayload(query=query, doc_type=doc_type).model_dump_json(),
        )
        if response.status_code == requests.status_codes.codes["ok"]:
            try:
                return SearchQueryResponsePayload.model_validate(response.json())
            except ValidationError as e:
                log.warning(
                    f"Impossible to convert get_all_documents response as SearchQueryResponsePayload : {response.json()}, details : {e}"
                )
        else:
            log.warning(f"POST query returned code [{response.status_code}]")
        return SearchQueryResponsePayload([], [], "")

    def get_document(self, document_id: str) -> GetDocumentResponsePayload:
        response = self.make_request(
            method="POST",
            endpoint=self.api_routes.get_document,
            data=GetDocumentPayload(document_id=document_id).model_dump_json(),
        )
        if response.status_code == requests.status_codes.codes["ok"]:
            try:
                return GetDocumentResponsePayload.model_validate(response.json())
            except ValidationError as e:
                log.warning(
                    f"Impossible to convert get_all_documents response as SearchQueryResponsePayload : {response.json()}, details : {e}"
                )
        else:
            log.warning(f"POST query returned code [{response.status_code}]")
        return GetDocumentResponsePayload({})

    def get_components(self) -> requests.Response:
        return self.make_request("GET", self.api_routes.get_components)

    def load_data(self, loadPayload: LoadPayload) -> LoadResponsePayload:
        log.info(
            f"Loading data with {len(loadPayload.fileNames)} documents (chunk size: {loadPayload.chunkUnits}, chunker: {loadPayload.chunker}, chunkOverlap: {loadPayload.chunkOverlap}, embedder: {loadPayload.embedder})"
        )
        response = self.make_request(
            method="POST",
            endpoint=self.api_routes.load_data,
            json=loadPayload.model_dump(),
        )
        if response.status_code == requests.status_codes.codes["ok"]:
            try:
                return LoadResponsePayload.model_validate(response.json())
            except ValidationError as e:
                log.warning(
                    f"Impossible to convert get_all_documents response as SearchQueryResponsePayload : {response.json()}, details : {e}"
                )
        else:
            log.error(
                f"POST query returned code [{response.status_code}] details {response.content}"
            )
        return LoadResponsePayload(
            status=response.status_code, status_msg=response.text
        )

    def delete_document(self, document_id: str) -> bool:
        response = self.make_request(
            method="POST",
            endpoint=self.api_routes.delete_document,
            data=GetDocumentPayload(document_id=document_id).model_dump_json(),
        )
        if response.status_code == requests.status_codes.codes["ok"]:
            return True
        else:
            log.warning(f"POST query returned code [{response.status_code}]")
            return False

    def set_openai_key(self, api_key: str) -> APIKeyResponsePayload:
        response = self.make_request(
            method="POST",
            endpoint=self.api_routes.set_openai_key,
            data=APIKeyPayload(key=api_key).model_dump_json(),
        )
        if response.status_code == requests.status_codes.codes["ok"]:
            try:
                return APIKeyResponsePayload.model_validate(response.json())
            except ValidationError as e:
                log.warning(
                    f"Impossible to convert set_openai_key response as APIKeyResponsePayload : {response.json()}, details : {e}"
                )
        else:
            log.error(
                f"POST query returned code [{response.status_code}] details {response.content}"
            )
        return LoadResponsePayload(
            status=response.status_code, status_msg=response.text
        )

    def get_openai_key_preview(self) -> str:
        response = self.make_request(
            "GET", self.api_routes.get_openai_key_preview
        ).json()

        if response["status"] == "200":
            return response["status_msg"]
        else:
            return ""

    def unset_openai_key(self) -> bool:
        response = self.make_request("POST", self.api_routes.unset_openai_key).json()
        return response["status"] == "200"

    def test_openai_api_key(self) -> Dict:
        response = self.make_request("GET", self.api_routes.test_openai_api_key)
        return response.json()


def test_api_connection(api_client: APIClient) -> dict:
    """
    Do a curl to the health check api endpoint

    :param APIClient api_client:
    :return dict:
    """
    try:
        response = api_client.health_check()
        if response.status_code == requests.status_codes.codes["ok"]:
            return {"is_ok": True}
        else:
            log.error(f"API health status code :{response.status_code}")
            log.error(f"API health content :{response.json()}")
            return {
                "is_ok": False,
                "error_details": f"API health status code : {response.status_code} - API health content : {response.json()}",
            }
    except (requests.exceptions.RequestException, RetryError) as e:
        log.error(f"Connection error, make sure verba is running details : {e}")
        return {
            "is_ok": False,
            "error_details": f"Connection error : {e} Make sure Verba is running or accessible",
        }
