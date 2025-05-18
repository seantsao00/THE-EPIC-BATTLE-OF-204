# scripts/add_admin.py
from getpass import getpass

from app.auth import get_password_hash
from app.database import SessionLocal
from app.models import User


def main():
    db = SessionLocal()
    username = input("Username: ")
    if db.query(User).filter_by(username=username).first():
        print("User already exists.")
        return
    password = getpass("Password: ")
    user = User(username=username, hashed_password=get_password_hash(password))
    db.add(user)
    db.commit()
    db.close()
    print("User added.")

if __name__ == "__main__":
    main()
