from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class QueryPayload(BaseModel):
    query: str


class DocumentChunk(BaseModel):
    text: str = ""
    doc_name: str = ""
    chunk_id: int
    doc_uuid: str
    doc_type: str
    score: float


class QueryResponsePayload(BaseModel):
    documents: List[DocumentChunk] = Field(default_factory=list)
    context: str = ""
    system: Optional[str] = None


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
    documents: List[DocumentSearchQueryResponsePayload] = Field(default_factory=list)
    doc_types: List[str] = Field(default_factory=list)
    current_embedder: str


class GetDocumentPayload(BaseModel):
    document_id: str


class GetDocumentResponsePayload(BaseModel):
    class DocumentResponsePayload(BaseModel):
        class DocumentPropertiesResponsePayload(BaseModel):
            chunk_count: int
            doc_link: str
            doc_name: str
            doc_type: str
            text: str
            timestamp: str

        document_class: str = Field(alias="class")
        creationTimeUnix: int
        id: str
        lastUpdateTimeUnix: int
        properties: DocumentPropertiesResponsePayload = Field(
            default_factory=DocumentPropertiesResponsePayload
        )
        tenant: str
        vectorWeights: Optional[Any]

    document: DocumentResponsePayload = Field(default_factory=DocumentResponsePayload)


class ConversationItem(BaseModel):
    type: str
    content: str
    typewriter: bool


class GeneratePayload(BaseModel):
    query: str
    context: str
    conversation: List[ConversationItem] = Field(default_factory=list)


class CachedResponse(BaseModel):
    message: str
    finish_reason: str
    cached: bool
    distance: float


class GenerateResponsePayload(BaseModel):
    system: str | CachedResponse = None


class ChunkerEnum(Enum):
    TOKENCHUNKER = "TokenChunker"
    WORDCHUNKER = "WordChunker"


class LoadPayload(BaseModel):
    reader: str = "SimpleReader"
    chunker: str = ChunkerEnum.TOKENCHUNKER.value
    embedder: str = "ADAEmbedder"
    fileBytes: List[str] = Field(default_factory=list)
    fileNames: List[str] = Field(default_factory=list)
    filePath: str = ""
    document_type: str
    chunkUnits: int = 100
    chunkOverlap: int = 500


class LoadResponsePayload(BaseModel):
    status: int
    status_msg: str


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
