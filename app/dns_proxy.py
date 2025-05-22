import asyncio
import queue
import socket
import threading

from dnslib import QTYPE, RR, A
from dnslib.server import BaseResolver, DNSLogger, DNSRecord, DNSServer

from .database import SessionLocal
from .llm_filter import is_domain_safe
from .models import DomainList, DomainLog, ListType, DomainStatus


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
        with SessionLocal() as db:
            print(f"Resolving {qname}")
            if db.query(DomainList).filter_by(domain=qname, list_type=ListType.whitelist.value).first():
                status = DomainStatus.allowed.value
                print(f"Domain {qname} is whitelisted")
            elif db.query(DomainList).filter_by(domain=qname, list_type=ListType.blacklist.value).first():
                status = DomainStatus.blocked.value
                print(f"Domain {qname} is blacklisted")
            else:
                print(f"Domain {qname} not in DB, enqueueing for LLM check...")
                status = DomainStatus.reviewed.value
                self.domain_llm_queue.put(qname)

            log = DomainLog(domain=qname, status=status)
            db.add(log)
            db.commit()

        if status == DomainStatus.blocked.value:
            reply = request.reply()
            reply.add_answer(RR(qname, QTYPE.A, rdata=A("0.0.0.0"), ttl=60))
            return reply
        else:
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
