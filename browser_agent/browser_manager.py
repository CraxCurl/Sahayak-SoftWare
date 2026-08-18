import asyncio
import os
from typing import List, Optional
from playwright.async_api import async_playwright, Playwright, Browser, BrowserContext, Page
from browser_agent.errors import BrowserAgentError

class BrowserManager:
    """
    Manages Playwright browser lifecycle, isolated contexts, pages, multi-tab switching,
    and crash recovery for Sahayak Browser Agent.
    """
    def __init__(self, headless: bool = False, viewport_width: int = 1280, viewport_height: int = 800):
        self.headless = headless
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.active_page: Optional[Page] = None
        self._is_initialized = False

    async def launch(self) -> Page:
        """Launches browser instance and opens initial page in isolated context."""
        if not self._is_initialized:
            try:
                self.playwright = await async_playwright().start()
                self.browser = await self.playwright.chromium.launch(
                    headless=self.headless,
                    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-notifications"]
                )
                self.context = await self.browser.new_context(
                    viewport={"width": self.viewport_width, "height": self.viewport_height},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    accept_downloads=True
                )
                
                # Attach listener to auto-register new tabs/popups
                self.context.on("page", self._on_page_created)

                self.active_page = await self.context.new_page()
                self._is_initialized = True
                print("[BrowserManager] Playwright Chromium launched successfully.")
            except Exception as e:
                raise BrowserAgentError(f"Failed to launch Playwright browser: {e}")

        return self.active_page

    def _on_page_created(self, page: Page):
        print(f"[BrowserManager] New tab detected: {page}")

    async def new_page(self, url: Optional[str] = None) -> Page:
        """Opens a new tab page."""
        if not self.context:
            await self.launch()
        
        page = await self.context.new_page()
        self.active_page = page
        if url:
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        return page

    async def get_current_page(self) -> Page:
        """Returns the currently active page."""
        if not self.active_page or self.active_page.is_closed():
            pages = await self.get_pages()
            if pages:
                self.active_page = pages[-1]
            else:
                self.active_page = await self.new_page()
        return self.active_page

    async def get_pages(self) -> List[Page]:
        """Returns list of all open pages/tabs in the context."""
        if not self.context:
            return []
        return [p for p in self.context.pages if not p.is_closed()]

    async def switch_page(self, index: int) -> Page:
        """Switches active page focus to the specified tab index."""
        pages = await self.get_pages()
        if 0 <= index < len(pages):
            self.active_page = pages[index]
            await self.active_page.bring_to_front()
            return self.active_page
        raise BrowserAgentError(f"Invalid tab index: {index}. Total tabs: {len(pages)}")

    async def close_page(self, page: Optional[Page] = None):
        """Closes target page or currently active page."""
        target = page or self.active_page
        if target and not target.is_closed():
            await target.close()
            pages = await self.get_pages()
            self.active_page = pages[-1] if pages else None

    async def close(self):
        """Closes browser and cleans up Playwright resources."""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            print(f"[BrowserManager Warning] Exception during browser close: {e}")
        finally:
            self.playwright = None
            self.browser = None
            self.context = None
            self.active_page = None
            self._is_initialized = False
            print("[BrowserManager] Browser closed cleanly.")
