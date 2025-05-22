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
        verbose=False
    )
    fit_md_generator = DefaultMarkdownGenerator(
        content_source="fit_html",
        options={"ignore_links": True}
    )
    run_config = CrawlerRunConfig(
        deep_crawl_strategy=BestFirstCrawlingStrategy(  # can be DFSDeepCrawlStrategy or BFSDeepCrawlStrategy
            max_depth=3,
            max_pages=3,
            include_external=False
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
                    print(f"Fetched {len(texts)} pages from {url}")
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
        print(text)
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

        if harmful:
            session.add(DomainList(domain=domain, list_type=ListType.blacklist, source=ListSource.llm))
        else:
            session.add(DomainList(domain=domain, list_type=ListType.whitelist, source=ListSource.llm))
        session.commit()
        return not harmful
