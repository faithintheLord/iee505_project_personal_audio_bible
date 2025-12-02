from fastapi import HTTPException, status
from sqlmodel import Session, select

from . import models


def ensure_manage(session: Session, user: models.Users, bible_id: int):
    auth = session.exec(select(models.Auths).where(models.Auths.user_id == user.user_id)).first()
    if not auth:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No auth record")
    link = session.exec(
        select(models.ManageAuths).where(
            models.ManageAuths.auth_id == auth.auth_id, models.ManageAuths.bible_id == bible_id
        )
    ).first()
    if not link:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No manage access")
    return auth


def ensure_listen(session: Session, user: models.Users, bible_id: int):
    auth = session.exec(select(models.Auths).where(models.Auths.user_id == user.user_id)).first()
    if not auth:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No auth record")
    link = session.exec(
        select(models.ListenAuths).where(
            models.ListenAuths.auth_id == auth.auth_id, models.ListenAuths.bible_id == bible_id
        )
    ).first()
    manage = session.exec(
        select(models.ManageAuths).where(
            models.ManageAuths.auth_id == auth.auth_id, models.ManageAuths.bible_id == bible_id
        )
    ).first()
    if not link and not manage:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No listen access")
    return auth


def word_count(text: str) -> int:
    return len([w for w in text.split() if w]) if text else 0
