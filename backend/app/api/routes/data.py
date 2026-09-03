from fastapi import APIRouter, Depends, File, UploadFile

from app.api.deps import get_runtime
from app.schemas.api import DatasetSummary
from app.services.dataset import build_summary, save_uploads
from app.services.runtime import AppRuntime

router = APIRouter(prefix="/data", tags=["data"])


@router.get("/summary", response_model=DatasetSummary)
def dataset_summary(runtime: AppRuntime = Depends(get_runtime)) -> DatasetSummary:
    return build_summary(runtime)


@router.post("/upload", response_model=DatasetSummary)
async def upload_dataset(
    files: list[UploadFile] = File(...),
    runtime: AppRuntime = Depends(get_runtime),
) -> DatasetSummary:
    return save_uploads(runtime, files)
