"""认证服务"""

from sqlalchemy.orm import Session

from app.core.exceptions import BizException
from app.core.security import verify_password
from app.models.user import User


def authenticate(db: Session, username: str, password: str) -> User:
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        raise BizException("用户名或密码错误", 401)
    if user.status != 1:
        raise BizException("账号已被禁用", 403)
    return user


def update_last_login(db: Session, user: User) -> None:
    from datetime import datetime

    user.last_login_at = datetime.now()
    db.commit()
