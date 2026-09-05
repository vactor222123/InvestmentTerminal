"""Execute one request selected from a checksum-bound private manifest."""

from dataclasses import dataclass

from investment_terminal.operations.market_batch_manifest import _manifest_checksum
from investment_terminal.operations.resumable_market_batch import (
    MarketBatchRequest,
    ResumableMarketBatchService,
)
from investment_terminal.utils.validation import normalize_required_text


@dataclass(frozen=True, slots=True)
class ManifestBatchSelection:
    manifest_checksum: str
    batch_index: int
    batch_count: int
    request: MarketBatchRequest

    @classmethod
    def from_manifest(
        cls,
        value: object,
        expected_manifest_checksum: str,
        batch_index: int,
    ) -> "ManifestBatchSelection":
        if isinstance(batch_index, bool) or not isinstance(batch_index, int):
            raise TypeError("batch_index must be an integer")
        expected = normalize_required_text(
            expected_manifest_checksum,
            field_name="manifest_checksum",
        ).lower()
        if not _is_sha256(expected):
            raise ValueError("manifest_checksum must be a SHA-256 value")
        if (
            not isinstance(value, dict)
            or value.get("schema_version") != 1
            or value.get("manifest_identity") != "QUALIFIED_MARKET_BATCH_MANIFEST"
        ):
            raise ValueError("Unsupported market batch manifest")
        if _manifest_checksum(value) != expected:
            raise ValueError("Manifest checksum does not match")
        if not _is_sha256(value.get("projection_checksum")) or not _is_sha256(
            value.get("currency_request_checksum")
        ):
            raise ValueError("Manifest evidence checksums are invalid")

        batches = value.get("batches")
        if (
            not isinstance(batches, list)
            or not batches
            or any(not isinstance(item, dict) for item in batches)
        ):
            raise ValueError("Manifest batches are invalid")
        indices = [item.get("batch_index") for item in batches]
        if indices != list(range(1, len(batches) + 1)):
            raise ValueError("Manifest batch indices must be ordered and contiguous")
        if not 1 <= batch_index <= len(batches):
            raise ValueError("batch_index is outside the manifest")

        selected = batches[batch_index - 1]
        request = MarketBatchRequest.from_dict(selected.get("request"))
        request_checksum = selected.get("request_checksum")
        if not _is_sha256(request_checksum) or request_checksum != request.checksum:
            raise ValueError("Manifest request checksum does not match")
        return cls(expected, batch_index, len(batches), request)


class ManifestBoundMarketBatchService:
    def __init__(self, *, importer, checkpoint_writer, clock) -> None:
        self.service = ResumableMarketBatchService(
            importer=importer,
            checkpoint_writer=checkpoint_writer,
            clock=clock,
        )

    def run(
        self,
        selection: ManifestBatchSelection,
        checkpoint: object | None = None,
    ) -> dict[str, object]:
        if not isinstance(selection, ManifestBatchSelection):
            raise TypeError("selection must be a ManifestBatchSelection")
        result = self.service.run(selection.request, checkpoint)
        return {
            "schema_version": 1,
            "operation_identity": "MANIFEST_BOUND_MARKET_BATCH",
            "provider_identity": result["provider_identity"],
            "status": result["status"],
            "started_at": result["started_at"],
            "completed_at": result["completed_at"],
            "duration_seconds": result["duration_seconds"],
            "manifest_checksum": selection.manifest_checksum,
            "batch_index": selection.batch_index,
            "batch_count": selection.batch_count,
            "request_checksum": selection.request.checksum,
            "coverage": result["coverage"],
            "failure_types": result["failure_types"],
            "limitations": [
                "report excludes symbols, currencies, paths, prices, provider text, and exception messages",
                "one-batch execution does not authorize another batch, a manifest drain, scheduling, analysis, or trading",
            ],
        }


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )
