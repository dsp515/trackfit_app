from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password, create_access_token
from app.models.user import User
from app.schemas.user import UserCreate


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def signup(self, user_data: UserCreate) -> User:
        existing = self.db.query(User).filter(User.email == user_data.email).first()
        if existing:
            raise ValueError("Email already registered")
        hashed = get_password_hash(user_data.password)
        db_user = User(
            email=user_data.email,
            hashed_password=hashed,
            name=user_data.name,
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def login(self, email: str, password: str) -> str:
        user = self.db.query(User).filter(User.email == email).first()
        if not user or not verify_password(password, user.hashed_password):
            raise ValueError("Incorrect email or password")
        return create_access_token(data={"sub": str(user.id)})

    def get_user_by_id(self, user_id: str) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()
