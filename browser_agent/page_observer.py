import urllib.parse
from typing import Dict, Any, Optional
from playwright.async_api import Page
from browser_agent.models import PageObservation
from browser_agent.dom_extractor import DOMExtractor
from browser_agent.accessibility import AccessibilityTreeParser
from browser_agent.screenshot import ScreenshotManager
from browser_agent.popup_detector import PopupDetector

class PageObserver:
    """Observes current Playwright Page and extracts DOM, Accessibility Tree, Screenshots, and Modal/Popup state."""

    @classmethod
    async def observe(cls, page: Page, is_initial_load: bool = False, take_screenshot_if_ambiguous: bool = False) -> PageObservation:
        url = page.url
        title = await page.title()
        parsed_url = urllib.parse.urlparse(url)
        hostname = parsed_url.netloc or "localhost"

        viewport_size = page.viewport_size or {"width": 1280, "height": 800}

        # 1. Tab information
        context = page.context
        all_pages = [p for p in context.pages if not p.is_closed()]
        tabs = []
        active_idx = 0
        for i, p in enumerate(all_pages):
            tabs.append({"id": f"tab-{i}", "url": p.url, "title": await p.title() if not p.is_closed() else ""})
            if p == page:
                active_idx = i

        # 2. Extract DOM interactive elements & Modal indicators
        dom_res = await DOMExtractor.extract_elements(page)
        elements = dom_res["elements"]
        has_modal = dom_res["has_modal"]
        modal_text = dom_res["modal_text"]

        # 3. Accessibility tree snapshot
        accessibility_tree = await AccessibilityTreeParser.get_accessibility_snapshot(page)

        # 4. Popup & Modal detection
        popup_info = PopupDetector.detect_popup(elements, modal_text, title)

        # 5. Adaptive screenshot capture
        should_snap = ScreenshotManager.should_take_screenshot(
            has_modal=has_modal or popup_info["detected"],
            is_ambiguous=take_screenshot_if_ambiguous,
            is_initial_load=is_initial_load
        )
        screenshot_b64 = await ScreenshotManager.capture_b64(page) if should_snap else None

        return PageObservation(
            url=url,
            title=title,
            hostname=hostname,
            viewport=viewport_size,
            tabs=tabs,
            active_tab_index=active_idx,
            elements=elements,
            accessibility_tree=accessibility_tree,
            screenshot_b64=screenshot_b64,
            has_modal=has_modal or popup_info["detected"],
            modal_title=popup_info["title"] if popup_info["detected"] else "",
            modal_text=modal_text,
            is_captcha=(popup_info.get("type") == "captcha"),
            is_otp=(popup_info.get("type") == "otp")
        )
