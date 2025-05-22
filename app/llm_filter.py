from typing import AsyncGenerator

import openai
from crawl4ai import (AsyncWebCrawler, BFSDeepCrawlStrategy, BrowserConfig, CacheMode,
                      CrawlerRunConfig, CrawlResult)
from sqlmodel import Session, select

from .database import engine
from .models import DomainList, ListSource, ListType
from .settings import settings


async def fetch_site_text(domain: str, timeout: int = 5, max_bytes: int = 5000) -> str:
    print(f"fetching '{domain}' text...")
    browser_config = BrowserConfig(
        browser_type="chromium",
        headless=True,
        verbose=False
    )
    run_config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(  # can be DFSDeepCrawlStrategy
            max_depth=2,
            max_pages=10,
            include_external=False
        ),
        page_timeout=timeout * 1000,  # ms
        cache_mode=CacheMode.BYPASS,  # can be ENABLED, BYPASS, READ_ONLY, WRITE_ONLY
        verbose=False
    )

    for scheme in ["https", "http"]:
        url = f"{scheme}://{domain.strip('.')}/"
        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(
                    url=url,
                    config=run_config
                )
                if not isinstance(result, AsyncGenerator):
                    res: CrawlResult = result[0]
                    if res and res.success and res.markdown:
                        return res.markdown[:max_bytes]

        except Exception as e:
            continue
    return ""


async def moderate_text(text: str) -> dict:
    if not text:
        return {"flagged": False, "categories": {}}
    try:
        response = await openai.AsyncOpenAI(api_key=settings.openai_api_key).moderations.create(
            model="omni-moderation-latest",
            input=text,
        )
        result = response.results[0]
        return {"flagged": result.flagged, "categories": result.categories}
    except Exception as e:
        print(f"OpenAI moderation error: {e}")
        return {"flagged": False, "categories": {}}


async def is_domain_safe(domain: str) -> bool:
    with Session(engine) as session:
        if session.exec(select(DomainList).where(DomainList.domain == domain, DomainList.list_type == ListType.blacklist)).first():
            return False
        if session.exec(select(DomainList).where(DomainList.domain == domain, DomainList.list_type == ListType.whitelist)).first():
            return True
        content = await fetch_site_text(domain)
        mod_result = await moderate_text(content)
        harmful = mod_result["flagged"] and mod_result["categories"].get("sexual", False)
        if harmful:
            session.add(DomainList(domain=domain, list_type=ListType.blacklist, source=ListSource.llm))
        else:
            session.add(DomainList(domain=domain, list_type=ListType.whitelist, source=ListSource.llm))
        session.commit()
        return not harmful
