import os

import openai
from crawl4ai import (
    AsyncWebCrawler,
    CrawlerRunConfig,
    BrowserConfig,
    CrawlResult,
    CacheMode
)
from typing import AsyncGenerator

from .database import SessionLocal
from .models import DomainList

async def fetch_site_text(domain: str, timeout: int = 5, max_bytes: int = 5000) -> str:
    browser_config = BrowserConfig(
        browser_type="chromium",
        headless=True,
        verbose=False
    )
    run_config = CrawlerRunConfig(
        page_timeout=timeout * 1000, # ms
        cache_mode=CacheMode.BYPASS, # convinent for testing fetching functionality
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
        response = await openai.AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"]).moderations.create(
            model="omni-moderation-latest",
            input=text,
        )
        result = response.results[0]
        return {"flagged": result.flagged, "categories": result.categories}
    except Exception as e:
        print(f"OpenAI moderation error: {e}")
        return {"flagged": False, "categories": {}}


async def is_domain_safe(domain: str) -> bool:
    with SessionLocal() as db:
        if db.query(DomainList).filter_by(domain=domain, list_type='blacklist').first():
            return False

        if db.query(DomainList).filter_by(domain=domain, list_type='whitelist').first():
            return True

        content = await fetch_site_text(domain)
        mod_result = await moderate_text(content)
        harmful = mod_result["flagged"] and getattr(mod_result["categories"], "sexual", False)

        if harmful:
            db.add(DomainList(domain=domain, list_type="blacklist"))
        else:
            db.add(DomainList(domain=domain, list_type="whitelist"))
        db.commit()

        return not harmful
