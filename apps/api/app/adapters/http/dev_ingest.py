from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.adapters.storage.jpeg import JpegAdmissionError, PillowJpegAdmission

router = APIRouter()
MAX_DEV_UPLOAD_BYTES = 8 * 1024 * 1024


@router.post("/dev/ingest", status_code=202)
async def ingest_development_jpeg(
    file: Annotated[UploadFile, File(...)],
) -> dict[str, str]:
    if file.content_type != "image/jpeg":
        raise HTTPException(status_code=415, detail="Only image/jpeg is accepted")

    contents = await file.read(MAX_DEV_UPLOAD_BYTES + 1)
    if len(contents) > MAX_DEV_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds the configured size limit")
    if not contents:
        raise HTTPException(status_code=415, detail="Image is empty")
    try:
        PillowJpegAdmission(max_bytes=MAX_DEV_UPLOAD_BYTES).admit(contents, file.content_type or "")
    except JpegAdmissionError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error

    return {"status": "accepted"}
