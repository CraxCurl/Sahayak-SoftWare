import base64
from typing import Optional
from playwright.async_api import Page

class ScreenshotManager:
    """Adaptive Screenshot Manager capturing visual snapshots when needed."""

    @classmethod
    async def capture_b64(cls, page: Page, full_page: bool = False) -> Optional[str]:
        """Captures page screenshot and returns base64 encoded string."""
        try:
            screenshot_bytes = await page.screenshot(full_page=full_page, timeout=5000)
            return base64.b64encode(screenshot_bytes).decode("utf-8")
        except Exception as e:
            print(f"[ScreenshotManager Error] Failed to capture screenshot: {e}")
            return None

    @classmethod
    def should_take_screenshot(cls, has_modal: bool, is_ambiguous: bool, is_initial_load: bool) -> bool:
        """Adaptive evaluation: determine if screenshot is necessary."""
        if is_initial_load or has_modal or is_ambiguous:
            return True
        return False
