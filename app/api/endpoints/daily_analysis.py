from fastapi import APIRouter
from app.api.schemas import DailyFeedbackRequest, DailyFeedbackResponse
from app.api.services import get_daily_feedback_service

router = APIRouter(prefix="/ai", tags=["Daily Analysis"])

@router.post("/analysis/daily", response_model=DailyFeedbackResponse)
async def create_daily_feedback(request: DailyFeedbackRequest):
    return await get_daily_feedback_service(request)