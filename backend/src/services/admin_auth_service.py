import uuid

import bcrypt

from src.database.database import SessionLocal
from src.database.models import AdminUser


class AdminAuthService:

    def authenticate(
        self,
        username: str,
        password: str,
    ) -> dict | None:

        username = username.strip()

        if not username or not password:
            return None

        with SessionLocal() as db:

            admin = (
                db.query(AdminUser)
                .filter(
                    AdminUser.username == username
                )
                .first()
            )

            if admin is None:
                return None

            try:
                valid_password = bcrypt.checkpw(
                    password.encode("utf-8"),
                    admin.password_hash.encode("utf-8"),
                )

            except (ValueError, TypeError):
                return None

            if not valid_password:
                return None

            return {
                "id": str(admin.id),
                "username": admin.username,
            }


    def create_admin(
        self,
        username: str,
        password: str,
    ) -> dict:

        username = username.strip()

        if len(username) < 3:
            raise ValueError(
                "Username must contain at least "
                "3 characters."
            )

        if len(password) < 8:
            raise ValueError(
                "Password must contain at least "
                "8 characters."
            )

        with SessionLocal() as db:

            existing = (
                db.query(AdminUser)
                .filter(
                    AdminUser.username == username
                )
                .first()
            )

            if existing is not None:
                raise ValueError(
                    "Admin username already exists."
                )

            password_hash = (
                bcrypt.hashpw(
                    password.encode("utf-8"),
                    bcrypt.gensalt(),
                )
                .decode("utf-8")
            )

            admin = AdminUser(
                username=username,
                password_hash=password_hash,
            )

            db.add(admin)
            db.commit()
            db.refresh(admin)

            return {
                "id": str(admin.id),
                "username": admin.username,
            }


    def change_password(
        self,
        admin_id: str,
        current_password: str,
        new_password: str,
    ) -> bool:

        if len(new_password) < 8:
            raise ValueError(
                "New password must contain at least "
                "8 characters."
            )

        try:
            parsed_admin_id = uuid.UUID(
                str(admin_id)
            )

        except (ValueError, TypeError):
            return False

        with SessionLocal() as db:

            admin = (
                db.query(AdminUser)
                .filter(
                    AdminUser.id == parsed_admin_id
                )
                .first()
            )

            if admin is None:
                return False

            try:
                current_valid = bcrypt.checkpw(
                    current_password.encode("utf-8"),
                    admin.password_hash.encode("utf-8"),
                )

            except (ValueError, TypeError):
                return False

            if not current_valid:
                return False

            new_password_hash = (
                bcrypt.hashpw(
                    new_password.encode("utf-8"),
                    bcrypt.gensalt(),
                )
                .decode("utf-8")
            )

            admin.password_hash = (
                new_password_hash
            )

            db.commit()

            return True


    def admin_exists(
        self,
    ) -> bool:

        with SessionLocal() as db:

            return (
                db.query(AdminUser.id)
                .first()
                is not None
            )


    def get_admin(
        self,
        admin_id: str,
    ) -> dict | None:

        try:
            parsed_admin_id = uuid.UUID(
                str(admin_id)
            )

        except (ValueError, TypeError):
            return None

        with SessionLocal() as db:

            admin = (
                db.query(AdminUser)
                .filter(
                    AdminUser.id == parsed_admin_id
                )
                .first()
            )

            if admin is None:
                return None

            return {
                "id": str(admin.id),
                "username": admin.username,
            }
