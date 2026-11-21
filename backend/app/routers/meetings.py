import os
import json
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_manager
from app.models.models import Meeting, MeetingStatus, User
from app.schemas.schemas import MeetingResponse, MeetingListItem
from app.services.transcription_service import (
    TranscriptionError,
    get_transcription_service,
)
from app.services.meeting_analysis_service import (
    get_meeting_analysis_service,
)

router = APIRouter(prefix="/api/meetings", tags=["Meetings"])

ALLOWED_AUDIO_EXT = {"mp3", "wav", "m4a", "ogg", "webm"}
ALLOWED_VIDEO_EXT = {"mp4", "mov", "avi", "mkv", "webm"}
ALLOWED_EXTENSIONS = ALLOWED_AUDIO_EXT | ALLOWED_VIDEO_EXT

ALLOWED_CONTENT_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/mp4",
    "audio/x-m4a",
    "audio/ogg",
    "audio/webm",
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/x-matroska",
    "video/webm",
    "application/octet-stream",
}

MAX_UPLOAD_SIZE = 500 * 1024 * 1024

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_extension(filename: str) -> str:
    return os.path.splitext(filename)[1].lower().lstrip(".")


def validate_file(file: UploadFile) -> None:
    filename = file.filename or ""
    ext = get_extension(filename)

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: .{ext or 'unknown'}. "
                   f"Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    content_type = file.content_type or ""
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        pass


async def save_upload_file(file: UploadFile) -> dict:
    original_filename = os.path.basename(file.filename or "")
    ext = get_extension(original_filename)
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    stored_path = os.path.join(UPLOAD_DIR, unique_name)

    abs_upload = os.path.abspath(UPLOAD_DIR)
    abs_stored = os.path.abspath(stored_path)
    if not abs_stored.startswith(abs_upload + os.sep) and abs_stored != abs_upload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename: path traversal detected.",
        )

    total_bytes = 0
    chunk_size = 1024 * 1024

    with open(stored_path, "wb") as f:
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > MAX_UPLOAD_SIZE:
                f.close()
                try:
                    os.remove(stored_path)
                except OSError:
                    pass
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE // (1024 * 1024)} MB.",
                )
            f.write(chunk)

    return {
        "original_filename": original_filename,
        "stored_path": stored_path,
        "content_type": file.content_type or "application/octet-stream",
        "file_size": total_bytes,
    }


@router.post("", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def upload_meeting(
    title: str = Form(..., min_length=1, max_length=500),
    description: Optional[str] = Form(None, max_length=5000),
    meeting_date: Optional[str] = Form(None),
    recording: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    if not recording.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided.",
        )

    validate_file(recording)

    saved = await save_upload_file(recording)

    parsed_meeting_date = None
    if meeting_date:
        try:
            parsed_meeting_date = datetime.fromisoformat(meeting_date.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid meeting_date format. Use ISO 8601.",
            )

    meeting = Meeting(
        title=title.strip(),
        description=description.strip() if description else None,
        original_filename=saved["original_filename"],
        recording_path=saved["stored_path"],
        content_type=saved["content_type"],
        file_size=saved["file_size"],
        status=MeetingStatus.UPLOADED,
        meeting_date=parsed_meeting_date,
        created_by_id=current_user.id,
    )

    db.add(meeting)
    db.commit()
    db.refresh(meeting)

    return meeting


@router.get("", response_model=List[MeetingListItem])
def list_manager_meetings(
    status: Optional[MeetingStatus] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    query = db.query(Meeting).filter(Meeting.created_by_id == current_user.id)

    if status is not None:
        query = query.filter(Meeting.status == status)

    meetings = (
        query.order_by(Meeting.created_at.desc())
        .offset(max(0, skip))
        .limit(min(max(1, limit), 500))
        .all()
    )

    return meetings


@router.get("/{meeting_id}", response_model=MeetingResponse)
def get_meeting_detail(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    meeting = (
        db.query(Meeting)
        .filter(
            Meeting.id == meeting_id,
            Meeting.created_by_id == current_user.id,
        )
        .first()
    )

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found or not authorized.",
        )

    return meeting


@router.post("/{meeting_id}/transcribe", response_model=MeetingResponse)
def transcribe_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    meeting = (
        db.query(Meeting)
        .filter(
            Meeting.id == meeting_id,
            Meeting.created_by_id == current_user.id,
        )
        .first()
    )
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found or not authorized.",
        )

    if meeting.status == MeetingStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Meeting transcription is already in progress.",
        )

    if (
        meeting.status == MeetingStatus.COMPLETED
        and meeting.transcript is not None
        and meeting.transcript != ""
    ):
        return meeting

    service = get_transcription_service()

    meeting.status = MeetingStatus.PROCESSING
    db.commit()

    try:
        transcript = service.transcribe_audio(meeting.recording_path)
    except FileNotFoundError:
        meeting.status = MeetingStatus.FAILED
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recording file not found on server.",
        )
    except TranscriptionError:
        meeting.status = MeetingStatus.FAILED
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Transcription failed. Please try again later.",
        )
    except Exception:
        meeting.status = MeetingStatus.FAILED
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Transcription failed. Please try again later.",
        )

    meeting.transcript = transcript
    meeting.status = MeetingStatus.COMPLETED
    db.commit()
    db.refresh(meeting)

    return meeting


def _has_analysis(meeting: Meeting) -> bool:
    return bool(
        meeting.summary
        and meeting.summary.strip()
        and meeting.key_decisions is not None
        and meeting.key_decisions.strip()
        and meeting.action_items_json is not None
        and meeting.action_items_json.strip()
    )


@router.post("/{meeting_id}/analyze", response_model=MeetingResponse)
def analyze_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    meeting = (
        db.query(Meeting)
        .filter(
            Meeting.id == meeting_id,
            Meeting.created_by_id == current_user.id,
        )
        .first()
    )
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found or not authorized.",
        )

    transcript = (meeting.transcript or "").strip()
    if not transcript:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Meeting transcript is missing. Run transcription first.",
        )

    if _has_analysis(meeting):
        return meeting

    service = get_meeting_analysis_service()

    try:
        analysis = service.analyze_transcript(transcript)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Meeting analysis failed. Please try again later.",
        )

    if not isinstance(analysis, dict):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Meeting analysis returned invalid results.",
        )

    summary = analysis.get("meeting_summary") or ""
    key_decisions = analysis.get("key_decisions") or []
    action_items = analysis.get("action_items") or []

    if not isinstance(summary, str):
        summary = ""
    if not isinstance(key_decisions, list):
        key_decisions = []
    if not isinstance(action_items, list):
        action_items = []

    try:
        meeting.summary = summary.strip()
        meeting.key_decisions = json.dumps(key_decisions, ensure_ascii=False)
        meeting.action_items_json = json.dumps(action_items, ensure_ascii=False)
        db.commit()
        db.refresh(meeting)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save analysis results.",
        )

    return meeting
