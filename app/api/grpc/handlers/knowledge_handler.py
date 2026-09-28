"""gRPC handler for knowledge document ingestion and deletion."""
from app.api.grpc.generated_stubs import get_stub
from app.api.grpc.mappers.knowledge_mapper import (
    to_chunks_response,
    to_delete_response,
    to_ingest_command,
    to_ingest_response,
    to_list_response,
)
from app.core.knowledge.services import ingestion_service
from app.util.logger import logger

_, _pb2_grpc = get_stub("knowledge_service")


class KnowledgeHandler(_pb2_grpc.KnowledgeServiceServicer):
    async def IngestDocument(self, request, context):
        command = to_ingest_command(request)
        logger.info(
            "KnowledgeService.IngestDocument bytes=%d lot_scoped=%s",
            len(command.file_data),
            bool(command.parking_lot_id),
        )
        return to_ingest_response(await ingestion_service.ingest(command))

    async def DeleteDocument(self, request, context):
        removed = await ingestion_service.delete(
            request.document_id,
            request.parking_lot_id or None,
            draft_only=request.draft_only,
        )
        return to_delete_response(removed)

    async def ListDocuments(self, request, context):
        documents = await ingestion_service.list(request.parking_lot_id or None)
        return to_list_response(documents)

    async def ListDocumentChunks(self, request, context):
        chunks = await ingestion_service.list_chunks(
            request.document_id, request.parking_lot_id or None, request.version_no
        )
        return to_chunks_response(chunks)
