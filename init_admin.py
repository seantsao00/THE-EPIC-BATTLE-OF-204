from getpass import getpass

from sqlmodel import Session, select

from app.auth import get_password_hash
from app.database import engine
from app.models import User


def main():
    with Session(engine) as session:
        username = input("Username: ")
        statement = select(User).where(User.username == username)
        user = next(session.execute(statement), (None,))[0]
        if user:
            print("User already exists.")
            return
        password = getpass("Password: ")
        user = User(username=username, hashed_password=get_password_hash(password))
        session.add(user)
        session.commit()
        print("User added.")


if __name__ == "__main__":
    main()
