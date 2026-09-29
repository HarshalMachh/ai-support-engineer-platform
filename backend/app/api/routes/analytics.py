from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_staff
from app.db.session import get_db
from app.schemas.analytics import AIAnalytics, TicketAnalytics
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"], dependencies=[Depends(require_staff)])


@router.get("/tickets", response_model=TicketAnalytics)
def ticket_analytics(db: Session = Depends(get_db)) -> TicketAnalytics:
    return analytics_service.ticket_analytics(db)


@router.get("/ai", response_model=AIAnalytics)
def ai_analytics(db: Session = Depends(get_db)) -> AIAnalytics:
    return analytics_service.ai_analytics(db)
