from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

import aiohttp
import openai
from crawl4ai import (
    AsyncWebCrawler,
    BestFirstCrawlingStrategy,
    BrowserConfig,
    CacheMode,
    CrawlerRunConfig,
    CrawlResult,
    DefaultMarkdownGenerator,
)
from sqlmodel import Session, select

from .database import engine
from .models import DomainList, ListSource, ListType
from .settings import settings


async def fetch_site_text(domain: str, timeout: int = 5, max_bytes: int = 5000) -> str:
    print(f"fetching '{domain}' text...")
    browser_config = BrowserConfig(
        browser_type="chromium",
        headless=True,
        headers={"Accept-Language": "en-US,en;q=0.9"},
        verbose=False
    )
    fit_md_generator = DefaultMarkdownGenerator(
        content_source="fit_html",
        options={"ignore_links": True}
    )
    run_config = CrawlerRunConfig(
        deep_crawl_strategy=BestFirstCrawlingStrategy(  # can be DFSDeepCrawlStrategy or BFSDeepCrawlStrategy
            max_depth=5,
            max_pages=7,
            include_external=True,
        ),
        page_timeout=timeout * 1000,  # ms
        cache_mode=CacheMode.BYPASS,  # can be ENABLED, BYPASS, READ_ONLY, WRITE_ONLY
        verbose=False,
        markdown_generator=fit_md_generator
    )

    # Try crawl4ai first
    for scheme in ["https", "http"]:
        url = f"{scheme}://{domain.strip('.')}/"
        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url, config=run_config)
                texts: list[str] = []
                if isinstance(result, AsyncGenerator):
                    async for res in result:
                        res: CrawlResult
                        if res and res.success and res.markdown:
                            texts.append(res.markdown)
                else:
                    for res in result:
                        res: CrawlResult
                        if res and res.success and res.markdown:
                            texts.append(res.markdown)
                if texts:
                    combined = "\n".join(texts)
                    return combined[:max_bytes]
        except Exception as e:
            print(f"Error fetching {url} with crawl4ai: {e}")
            continue

    # Fallback to aiohttp if crawl4ai fails
    for scheme in ["https", "http"]:
        url = f"{scheme}://{domain.strip('.')}/"
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        return text[:max_bytes]
        except Exception as e:
            print(f"Error fetching {url} with aiohttp: {e}")
            continue
    return ""


async def moderate_text(text: str) -> bool:
    if not text:
        return False
    try:
        response = await openai.AsyncOpenAI(api_key=settings.openai_api_key).moderations.create(
            model="omni-moderation-latest",
            input=text,
        )
        result = response.results[0]
        return result.flagged and result.categories.sexual
    except openai.OpenAIError as e:
        print(f"OpenAI error: {e}")
        return False
    except Exception as e:
        print(f"unexpected error: {e}")
        return False


async def is_domain_safe(domain: str) -> bool:
    with Session(engine) as session:
        if session.exec(
            select(DomainList).where(
                DomainList.domain == domain,
                DomainList.list_type == ListType.blacklist)).first():
            return False
        if session.exec(
            select(DomainList).where(
                DomainList.domain == domain,
                DomainList.list_type == ListType.whitelist)).first():
            return True

        content = await fetch_site_text(domain)
        harmful = await moderate_text(content)

        print(f"Moderation result for {domain}: {harmful}")

        list_type = ListType.blacklist if harmful else ListType.whitelist
        session.add(DomainList(
            domain=domain,
            list_type=list_type,
            source=ListSource.llm,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1)
        ))
        session.commit()
        return not harmful
