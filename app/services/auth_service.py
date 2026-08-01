"""认证服务"""

from sqlalchemy.orm import Session

from app.core.exceptions import BizException
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import UserOut


def authenticate(db: Session, username: str, password: str) -> User:
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        raise BizException("用户名或密码错误", 401)
    if user.status != 1:
        raise BizException("账号已被禁用", 403)
    return user


def get_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def create_user(db: Session, username: str, password: str, real_name: str = "", role: str = "analyst") -> User:
    if get_by_username(db, username):
        raise BizException("用户名已存在")
    user = User(
        username=username,
        password_hash=hash_password(password),
        real_name=real_name,
        role=role,
        status=1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_last_login(db: Session, user: User) -> None:
    from datetime import datetime

    user.last_login_at = datetime.now()
    db.commit()


def to_out(user: User) -> UserOut:
    return UserOut.model_validate(user)
