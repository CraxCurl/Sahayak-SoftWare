import types
if not hasattr(types, "UnionType"):
    types.UnionType = type("UnionType", (), {})

import sys
from ui.overlay_widget import SahayakOverlay

def main():
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    print("[Sahayak] Starting Sahayak Assistant Floating Overlay...")
    app = SahayakOverlay()
    app.mainloop()

if __name__ == "__main__":
    main()
