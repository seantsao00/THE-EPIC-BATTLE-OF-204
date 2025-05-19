import asyncio
import socket
import threading

from dnslib.server import BaseResolver, DNSLogger, DNSRecord, DNSServer

from .database import SessionLocal
from .llm_filter import is_domain_safe
from .models import DomainList, DomainLog


class FilteringResolver(BaseResolver):
    def resolve(self, request, handler):
        qname = str(request.q.qname)
        with SessionLocal() as db:
            # Check whitelist
            print(f"Resolving {qname}")
            if db.query(DomainList).filter_by(domain=qname, list_type='whitelist').first():
                status = 'allowed'
                print(f"Domain {qname} is whitelisted")
            elif db.query(DomainList).filter_by(domain=qname, list_type='blacklist').first():
                status = 'blocked'
                print(f"Domain {qname} is blacklisted")
            else:
                print(f"Domain {qname} not in DB, checking with LLM...")
                status = 'allowed'
                def background_llm_check(domain):
                    def run():
                        asyncio.run(is_domain_safe(domain))
                    threading.Thread(target=run, daemon=True).start()
                background_llm_check(qname)
            # Log
            log = db.query(DomainLog).filter_by(domain=qname).first()
            if log:
                log.count += 1 # type: ignore
            else:
                log = DomainLog(domain=qname, status=status)
                db.add(log)
            db.commit()
        # Forward or block
        if status == 'blocked':
            from dnslib import QTYPE, RR, A
            reply = request.reply()
            reply.add_answer(RR(qname, QTYPE.A, rdata=A("0.0.0.0"), ttl=60))
            return reply
        else:
            # Forward to public DNS (8.8.8.8), real-world: support fallback/upstreams.
            upstream_ip = "8.8.8.8"
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(request.pack(), (upstream_ip, 53))
            data, _ = sock.recvfrom(4096)
            return DNSRecord.parse(data)


def start_dns_proxy(port=5353):
    resolver = FilteringResolver()
    logger = DNSLogger(prefix=False)
    server = DNSServer(resolver, port=port, address="127.0.0.1", logger=logger)
    server.start_thread()
