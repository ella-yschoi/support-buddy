"""Shared test fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_knowledge_dir(tmp_path: Path) -> Path:
    """Create a temp directory with sample knowledge docs."""
    kb_dir = tmp_path / "knowledge"
    kb_dir.mkdir()

    (kb_dir / "faq.md").write_text(
        "---\n"
        "title: CloudSync FAQ\n"
        "category: faq\n"
        "---\n\n"
        "## How do I reset my sync?\n\n"
        "Go to Settings > Sync > Reset. This will re-index all files.\n\n"
        "## What file types are supported?\n\n"
        "CloudSync supports all file types up to 5GB per file.\n"
    )

    (kb_dir / "error_codes.md").write_text(
        "---\n"
        "title: Error Code Reference\n"
        "category: error_code\n"
        "---\n\n"
        "## SYNC-001: File Conflict\n\n"
        "Two devices modified the same file simultaneously.\n"
        "Resolution: Open the conflict resolver in the dashboard.\n\n"
        "## SYNC-002: Upload Failed\n\n"
        "File upload to cloud storage failed.\n"
        "Resolution: Check network connectivity and retry. "
        "If persistent, check storage quota.\n"
    )

    (kb_dir / "troubleshooting.md").write_text(
        "---\n"
        "title: Sync Troubleshooting Guide\n"
        "category: troubleshooting\n"
        "---\n\n"
        "## Files Not Syncing\n\n"
        "1. Check if the sync agent is running (tray icon should be green)\n"
        "2. Verify network connectivity\n"
        "3. Check if the file exceeds the 5GB size limit\n"
        "4. Look for error codes in Settings > Logs\n\n"
        "## Slow Sync Performance\n\n"
        "1. Check available bandwidth\n"
        "2. Reduce the number of concurrent sync threads in Settings\n"
        "3. Exclude large binary files from sync\n"
    )

    return kb_dir


@pytest.fixture
def sample_json_logs() -> str:
    return """[
{"timestamp": "2024-01-15T10:00:00Z", "level": "INFO", "message": "Sync started", "service": "sync-engine"},
{"timestamp": "2024-01-15T10:00:05Z", "level": "INFO", "message": "Processing 150 files", "service": "sync-engine"},
{"timestamp": "2024-01-15T10:00:30Z", "level": "WARN", "message": "Slow upload detected: 25s for file_large.zip", "service": "sync-engine", "duration_ms": 25000},
{"timestamp": "2024-01-15T10:01:00Z", "level": "ERROR", "message": "Upload failed: SYNC-002 - storage quota exceeded", "service": "sync-engine", "error_code": "SYNC-002"},
{"timestamp": "2024-01-15T10:01:01Z", "level": "ERROR", "message": "Retry 1/3 failed for file_large.zip", "service": "sync-engine"},
{"timestamp": "2024-01-15T10:01:05Z", "level": "INFO", "message": "Sync completed with errors: 148/150 files synced", "service": "sync-engine"}
]"""


@pytest.fixture
def sample_text_logs() -> str:
    return (
        "2024-01-15 10:00:00 INFO  [sync-engine] Sync started\n"
        "2024-01-15 10:00:05 INFO  [sync-engine] Processing 150 files\n"
        "2024-01-15 10:00:30 WARN  [sync-engine] Slow upload detected: 25s for file_large.zip\n"
        "2024-01-15 10:01:00 ERROR [sync-engine] Upload failed: SYNC-002 - storage quota exceeded\n"
        "2024-01-15 10:01:01 ERROR [sync-engine] Retry 1/3 failed for file_large.zip\n"
        "2024-01-15 10:01:05 INFO  [sync-engine] Sync completed with errors: 148/150 files synced\n"
    )
