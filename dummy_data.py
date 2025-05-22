import random
from datetime import datetime, timedelta
from sqlmodel import Session, select
from app.database import engine
from app.models import DomainLog, DomainList, ListType, ListSource

def random_domain():
    return f"example{random.randint(1, 10000)}.com"

def random_ip():
    return ".".join(str(random.randint(0, 255)) for _ in range(4))

def create_dummy_logs(session, count=500):
    logs = []
    for i in range(count):
        log = DomainLog(
            domain=random_domain(),
            ip=random_ip(),
            timestamp=datetime.now() - timedelta(minutes=random.randint(0, 10000)),
            status=random.choice(["allowed", "blocked"]),
            list_type=random.choice([ListType.whitelist, ListType.blacklist])
        )
        logs.append(log)
    session.add_all(logs)
    session.commit()

def create_dummy_lists(session, count=500):
    lists = []
    # Get existing domains from the database using ORM
    existing_domains = set(row for row in session.exec(select(DomainList.domain)).all())
    # Generate unique domains not already in the database
    unique_domains = set()
    while len(unique_domains) < count:
        d = f"dummy{random.randint(1, 100000)}.com"
        if d not in existing_domains:
            unique_domains.add(d)
    unique_domains = list(unique_domains)
    half = count // 2
    for i, domain in enumerate(unique_domains):
        if i < half:
            lists.append(DomainList(
                domain=domain,
                list_type=ListType.whitelist,
                source=ListSource.manual
            ))
        else:
            lists.append(DomainList(
                domain=domain,
                list_type=ListType.blacklist,
                source=ListSource.manual
            ))
    session.add_all(lists)
    session.commit()

def main():
    with Session(engine) as session:
        create_dummy_logs(session)
        create_dummy_lists(session)

if __name__ == "__main__":
    main()