from typing import Any, List, Optional

from pydantic import BaseModel, Field


class QueryPayload(BaseModel):
    query: str


class QueryResponsePayload(BaseModel):
    system: Optional[str]
    context: str = ""
    documents: List[dict] = []


class DocumentChunk(BaseModel):
    text: str
    doc_name: str
    chunk_id: int
    doc_uuid: str
    doc_type: str
    score: str


class QueryResponsePayload(BaseModel):
    documents: List[DocumentChunk] = []
    context: str = ""
    system: Optional[str] = None


class APIKeyPayload(BaseModel):
    key: str


class SearchQueryPayload(BaseModel):
    query: Optional[str] = ""
    doc_type: Optional[str] = ""


class DocumentSearchQueryResponsePayload(BaseModel):
    class AdditionalItem(BaseModel):
        id: str = ""

    additional: AdditionalItem = Field(alias="_additional", default=AdditionalItem())
    doc_link: str = ""
    doc_name: str = ""
    doc_type: str = ""


class SearchQueryResponsePayload(BaseModel):
    documents: List[DocumentSearchQueryResponsePayload]
    doc_types: List
    current_embedder: str


class GetDocumentPayload(BaseModel):
    document_id: str


class GetDocumentResponsePayload(BaseModel):
    class DocumentResponsePayload(BaseModel):
        class DocumentPropertiesResponsePayload(BaseModel):
            chunk_count: int = 0
            doc_link: str = ""
            doc_name: str = ""
            doc_type: str = ""
            text: str = ""
            timestamp: str = ""

        document_class: str = Field(alias="class", default="")
        creationTimeUnix: int = 0
        id: str = ""
        lastUpdateTimeUnix: int = 0
        properties: DocumentPropertiesResponsePayload = (
            DocumentPropertiesResponsePayload()
        )
        tenant: str = ""
        vectorWeights: Any = None

    document: DocumentResponsePayload = DocumentResponsePayload()


class ConversationItem(BaseModel):
    type: str
    content: str
    typewriter: bool


class GeneratePayload(BaseModel):
    query: str
    context: str
    conversation: List[ConversationItem]


class CachedResponse(BaseModel):
    message: str
    finish_reason: str
    cached: bool
    distance: float


class GenerateResponsePayload(BaseModel):
    system: str | CachedResponse = None


class LoadPayload(BaseModel):
    reader: str = "SimpleReader"
    chunker: str = "WordChunker"
    embedder: str = "ADAEmbedder"
    fileBytes: List[str] = []
    fileNames: List[str] = []
    filePath: str = ""
    document_type: str = ""
    chunkUnits: int = 100
    chunkOverlap: int = 50


class LoadResponsePayload(BaseModel):
    status: int = 0
    status_msg: str = ""


class GetComponentPayload(BaseModel):
    component: str


class SetComponentPayload(BaseModel):
    component: str
    selected_component: str


class APIKeyPayload(BaseModel):
    key: str


class APIKeyResponsePayload(BaseModel):
    status: str
    status_msg: str
