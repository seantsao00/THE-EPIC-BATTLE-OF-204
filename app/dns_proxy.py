import asyncio
import queue
import socket
import threading
from datetime import datetime, timezone

from dnslib import QTYPE, RR, A
from dnslib.server import BaseResolver, DNSLogger, DNSRecord, DNSServer
from sqlmodel import Session, select

from .database import engine
from .llm_filter import is_domain_safe
from .models import DomainList, DomainLog, DomainStatus, ListType


class FilteringResolver(BaseResolver):
    def __init__(self):
        super().__init__()
        self.domain_llm_queue = queue.Queue()

        self.llm_thread = threading.Thread(
            target=lambda: asyncio.run(self._process_queue()), daemon=True)
        self.llm_thread.start()

    async def _process_queue(self):
        loop = asyncio.get_event_loop()
        while True:
            domain = await loop.run_in_executor(None, self.domain_llm_queue.get)
            if domain is None:
                break
            try:
                await is_domain_safe(domain)
            finally:
                self.domain_llm_queue.task_done()

    def resolve(self, request, handler):
        qname = str(request.q.qname)
        with Session(engine) as session:
            print(f"Resolving {qname}")

            entries = session.exec(select(DomainList).where(DomainList.domain == qname)).all()

            status = DomainStatus.reviewed
            for entry in entries:
                if entry.expires_at is None or entry.expires_at > datetime.now(timezone.utc).replace(tzinfo=None):
                    if entry.list_type == ListType.blacklist:
                        print(f"Domain {qname} is expired and blacklisted")
                        status = DomainStatus.blocked
                    elif entry.list_type == ListType.whitelist:
                        print(f"Domain {qname} is expired and whitelisted")
                        status = DomainStatus.allowed

            if status == DomainStatus.reviewed:
                print(f"Domain {qname} not found in DB, checking lists...")
                self.domain_llm_queue.put(qname)

            log = DomainLog(domain=qname, status=status)
            session.add(log)
            session.commit()

        if status == DomainStatus.blocked.value:
            reply = request.reply()
            reply.add_answer(RR(qname, QTYPE.A, rdata=A("0.0.0.0"), ttl=60))
            return reply

        upstream_ip = "8.8.8.8"
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(request.pack(), (upstream_ip, 53))
        data, _ = sock.recvfrom(4096)
        return DNSRecord.parse(data)


def start_dns_proxy(ip="127.0.0.1", port=5353):
    resolver = FilteringResolver()
    logger = DNSLogger(prefix=False)
    server = DNSServer(resolver, port=port, address=ip, logger=logger)
    server.start_thread()
