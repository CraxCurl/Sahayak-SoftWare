import json
from typing import List, Dict, Any
from playwright.async_api import Page
from browser_agent.models import DOMElement

JS_DOM_EXTRACTOR = """
() => {
    function isVisible(el) {
        if (!el) return false;
        const style = window.getComputedStyle(el);
        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
        const rect = el.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
    }

    function getRole(el) {
        if (el.getAttribute('role')) return el.getAttribute('role');
        const tag = el.tagName.toLowerCase();
        if (tag === 'button' || (tag === 'input' && (el.type === 'button' || el.type === 'submit'))) return 'button';
        if (tag === 'a') return 'link';
        if (tag === 'input' && (el.type === 'text' || el.type === 'search' || el.type === 'email' || el.type === 'password' || el.type === 'tel' || el.type === 'number')) return 'textbox';
        if (tag === 'input' && el.type === 'checkbox') return 'checkbox';
        if (tag === 'input' && el.type === 'radio') return 'radio';
        if (tag === 'textarea') return 'textbox';
        if (tag === 'select') return 'combobox';
        return tag;
    }

    const interactiveSelectors = 'button, a[href], input, textarea, select, [role="button"], [role="link"], [role="checkbox"], [role="radio"], [role="combobox"], [role="option"], [tabindex]:not([tabindex="-1"])';
    const elements = Array.from(document.querySelectorAll(interactiveSelectors));
    const modals = Array.from(document.querySelectorAll('[role="dialog"], [role="alertdialog"], .modal, .popup, .alert, dialog'));

    const results = [];
    let counter = 1;

    elements.forEach(function(el) {
        if (!isVisible(el)) return;
        
        const rect = el.getBoundingClientRect();
        const role = getRole(el);
        const text = (el.innerText || el.value || el.placeholder || '').trim().replace(/\\s+/g, ' ').substring(0, 100);
        const ariaLabel = el.getAttribute('aria-label') || el.getAttribute('title') || '';
        const placeholder = el.getAttribute('placeholder') || '';
        const isModal = modals.some(function(m) { return m.contains(el); });

        let selector = '';
        if (el.id) {
            selector = '#' + el.id;
        } else if (el.name) {
            selector = el.tagName.toLowerCase() + '[name="' + el.name + '"]';
        } else if (text) {
            selector = el.tagName.toLowerCase() + ':has-text("' + text.substring(0, 15) + '")';
        } else {
            selector = el.tagName.toLowerCase();
        }

        results.push({
            id: 'e-' + counter++,
            tag: el.tagName.toLowerCase(),
            role: role,
            text: text,
            aria_label: ariaLabel,
            placeholder: placeholder,
            visible: true,
            enabled: !el.disabled,
            clickable: true,
            bounding_box: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
            selector: selector,
            is_modal_element: isModal,
            attributes: {
                id: el.id || '',
                name: el.name || '',
                type: el.type || '',
                class: el.className || ''
            }
        });
    });

    return {
        elements: results.slice(0, 50),
        has_modal: modals.some(function(m) { return isVisible(m); }),
        modal_text: modals.map(function(m) { return m.innerText || ''; }).join('\\n').substring(0, 300)
    };
}
"""


class DOMExtractor:
    """Extracts compressed, structured, visible interactive DOM elements from Playwright Page."""

    @classmethod
    async def extract_elements(cls, page: Page) -> Dict[str, Any]:
        """Extracts visible interactive DOM elements and popup dialog indicators."""
        try:
            dom_data = await page.evaluate(JS_DOM_EXTRACTOR)
            elements = []
            for item in dom_data.get("elements", []):
                elements.append(DOMElement(
                    id=item["id"],
                    tag=item["tag"],
                    role=item["role"],
                    text=item["text"],
                    aria_label=item["aria_label"],
                    placeholder=item["placeholder"],
                    visible=item["visible"],
                    enabled=item["enabled"],
                    clickable=item["clickable"],
                    bounding_box=item["bounding_box"],
                    selector=item["selector"],
                    is_modal_element=item["is_modal_element"],
                    attributes=item["attributes"]
                ))
            return {
                "elements": elements,
                "has_modal": dom_data.get("has_modal", False),
                "modal_text": dom_data.get("modal_text", "")
            }
        except Exception as e:
            print(f"[DOMExtractor Error] Failed to extract elements: {e}")
            return {"elements": [], "has_modal": False, "modal_text": ""}
