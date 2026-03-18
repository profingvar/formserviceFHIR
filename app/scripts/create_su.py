#!/usr/bin/env python3
"""Bootstrap superuser from .env values. Idempotent — skips if SU email already exists."""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import bcrypt
from src.db import init_db, get_session
import src.models  # noqa: F401
from src.models.user import User
from src.models.professional import Professional


def main():
    database_url = os.environ.get('DATABASE_URL')
    su_email = os.environ.get('BOOTSTRAP_SU_EMAIL')
    su_password = os.environ.get('BOOTSTRAP_SU_PASSWORD')

    if not all([database_url, su_email, su_password]):
        print("ERROR: DATABASE_URL, BOOTSTRAP_SU_EMAIL, and BOOTSTRAP_SU_PASSWORD must be set.")
        sys.exit(1)

    if len(su_password) < 8:
        print("ERROR: BOOTSTRAP_SU_PASSWORD must be at least 8 characters.")
        sys.exit(1)

    init_db(database_url)
    session = get_session()

    try:
        existing = session.query(User).filter_by(email=su_email).first()
        if existing:
            print(f"Superuser {su_email} already exists (guid={existing.guid}). Skipping.")
            return

        password_hash = bcrypt.hashpw(su_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        user = User(
            guid=str(uuid.uuid4()),
            email=su_email,
            password_hash=password_hash,
            user_type='professional',
            is_su_admin=True,
        )
        session.add(user)
        session.flush()

        professional = Professional(
            guid=str(uuid.uuid4()),
            user_id=user.id,
            professional_role='other',
            first_name='System',
            last_name='Administrator',
        )
        session.add(professional)
        session.commit()

        print(f"Superuser created: {su_email} (guid={user.guid})")

    except Exception as e:
        session.rollback()
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        session.close()


if __name__ == '__main__':
    main()
