"""Map Knowledge protobuf messages to/from domain DTOs."""
from app.api.grpc.generated_stubs import get_stub
from app.core.knowledge.dtos.knowledge_dto import IngestDocumentCommand, IngestResult

_pb2, _ = get_stub("knowledge_service")


def to_ingest_command(message) -> IngestDocumentCommand:
    return IngestDocumentCommand(
        file_data=message.file_data,
        file_name=message.file_name,
        parking_lot_id=message.parking_lot_id or None,
        category=message.category or "regulation",
        uploaded_by=message.uploaded_by or None,
        document_id=message.document_id or None,
    )


def to_ingest_response(result: IngestResult):
    return _pb2.IngestDocumentResponse(
        document_id=result.document_id,
        status=_pb2.IngestStatus.Value(result.status.value),
        chunk_count=result.chunk_count,
        message=result.message,
        process_time_ms=result.process_time * 1000,
    )


def to_delete_response(removed_chunk_count: int):
    return _pb2.DeleteDocumentResponse(
        deleted=removed_chunk_count > 0,
        removed_chunk_count=removed_chunk_count,
    )
