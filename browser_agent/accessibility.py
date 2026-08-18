from typing import Optional, Dict, Any
from playwright.async_api import Page

class AccessibilityTreeParser:
    """Extracts and parses Playwright Accessibility Tree for semantic page reasoning."""

    @classmethod
    async def get_accessibility_snapshot(cls, page: Page) -> str:
        """Obtains semantic accessibility tree snapshot from Playwright Page."""
        try:
            tree = await page.accessibility.snapshot(interesting_only=True)
            if not tree:
                return "Accessibility tree unavailable."
            return cls._format_tree_node(tree, indent=0)
        except Exception as e:
            return f"Accessibility extraction error: {e}"

    @classmethod
    def _format_tree_node(cls, node: Dict[str, Any], indent: int = 0) -> str:
        lines = []
        role = node.get("role", "node")
        name = node.get("name", "").strip()
        value = node.get("value", "").strip()
        
        prefix = "  " * indent
        node_str = f"{prefix}{role}"
        if name:
            node_str += f": '{name}'"
        if value:
            node_str += f" (value='{value}')"
            
        lines.append(node_str)

        children = node.get("children", [])
        for child in children[:15]:  # Limit child depth for compact context
            lines.append(cls._format_tree_node(child, indent + 1))

        return "\n".join(lines)
