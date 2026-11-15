from sqlalchemy.orm import Session

from .models import ActivityLog, Notification, User


def log_activity(db: Session, user: User, action: str, entity: str,
                 entity_id: int | None = None, detail: str | None = None):
    db.add(ActivityLog(company_id=user.company_id, user_id=user.id, action=action,
                       entity=entity, entity_id=entity_id, detail=detail))


def notify(db: Session, company_id: int, message: str, level: str = "info"):
    db.add(Notification(company_id=company_id, message=message, level=level))
