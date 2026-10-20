import os
import math
from PIL import Image, ImageDraw, ImageFilter

OUT_DIR = os.path.join(os.path.dirname(__file__), 'electron', 'resources', 'tray_icons')
os.makedirs(OUT_DIR, exist_ok=True)

SIZE = 128
TARGET_SIZE = 32
CYAN = (0, 240, 255, 255)
WHITE = (240, 246, 252, 255)
RED = (248, 113, 113, 255)
AMBER = (251, 191, 36, 255)

def save_icon(img, name):
    res = img.resize((TARGET_SIZE, TARGET_SIZE), Image.Resampling.LANCZOS)
    path = os.path.join(OUT_DIR, f"{name}.png")
    res.save(path, "PNG")
    print(f"Generated {path}")

# 1. logo.png (Infinity symbol)
def make_logo():
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Draw infinity curve
    points = []
    # Parametric infinity: x = a*cos(t)/(1+sin^2(t)), y = a*sin(t)*cos(t)/(1+sin^2(t))
    scale = 44
    cx, cy = SIZE // 2, SIZE // 2
    for step in range(360):
        t = math.radians(step)
        denom = 1 + (math.sin(t) ** 2)
        x = cx + (scale * math.cos(t)) / denom
        y = cy + (scale * math.sin(t) * math.cos(t) * 1.5) / denom
        points.append((x, y))
    
    # Draw thick stroke with glow
    for i in range(len(points)):
        p1 = points[i]
        p2 = points[(i + 1) % len(points)]
        d.line([p1, p2], fill=CYAN, width=12)
    save_icon(img, "logo")

# 2. window.png (Desktop App window)
def make_window():
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Window outer frame
    d.rounded_rectangle([18, 22, 110, 106], radius=14, outline=CYAN, width=10)
    # Title bar separator
    d.line([18, 48, 110, 48], fill=CYAN, width=8)
    # Dots on titlebar
    d.ellipse([30, 31, 38, 39], fill=CYAN)
    d.ellipse([46, 31, 54, 39], fill=CYAN)
    save_icon(img, "window")

# 3. browser.png (Web Globe)
def make_browser():
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Outer circle
    d.ellipse([18, 18, 110, 110], outline=CYAN, width=10)
    # Equator line
    d.line([18, 64, 110, 64], fill=CYAN, width=8)
    # Vertical meridian ellipse
    d.ellipse([42, 18, 86, 110], outline=CYAN, width=8)
    save_icon(img, "browser")

# 4. folder.png (Downloads folder)
def make_folder():
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Folder tab and body
    # Tab: 20, 32 -> 54, 32 -> 62, 44 -> 108, 44
    tab_pts = [(18, 44), (18, 32), (50, 32), (62, 44), (110, 44), (110, 102), (18, 102)]
    d.polygon(tab_pts, fill=None)
    d.rounded_rectangle([18, 42, 110, 102], radius=10, outline=CYAN, width=10)
    # Tab outline
    d.line([(18, 44), (18, 32), (50, 32), (62, 44), (110, 44)], fill=CYAN, width=10)
    # Down arrow in folder
    d.line([64, 56, 64, 84], fill=WHITE, width=8)
    d.line([50, 72, 64, 84], fill=WHITE, width=8)
    d.line([78, 72, 64, 84], fill=WHITE, width=8)
    save_icon(img, "folder")

# 5. refresh.png (Restart engine)
def make_refresh():
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Arc
    d.arc([22, 22, 106, 106], start=40, end=320, fill=CYAN, width=10)
    # Arrow head at end
    d.polygon([(90, 20), (114, 38), (86, 48)], fill=CYAN)
    save_icon(img, "refresh")

# 6. update.png (Check for updates - spark/radar)
def make_update():
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Arrow pointing down into tray
    d.line([64, 18, 64, 76], fill=CYAN, width=10)
    d.line([44, 56, 64, 76], fill=CYAN, width=10)
    d.line([84, 56, 64, 76], fill=CYAN, width=10)
    # Tray bracket below
    d.line([(24, 84), (24, 104), (104, 104), (104, 84)], fill=CYAN, width=10)
    save_icon(img, "update")

# 7. autostart.png (Windows startup - off/neutral)
def make_autostart():
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Windows-style 4 tiles
    d.rounded_rectangle([22, 22, 58, 58], radius=6, outline=CYAN, width=8)
    d.rounded_rectangle([70, 22, 106, 58], radius=6, outline=CYAN, width=8)
    d.rounded_rectangle([22, 70, 58, 106], radius=6, outline=CYAN, width=8)
    d.rounded_rectangle([70, 70, 106, 106], radius=6, outline=CYAN, width=8)
    save_icon(img, "autostart")

# 7b. autostart_on.png (Windows startup - on/active)
def make_autostart_on():
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([22, 22, 58, 58], radius=6, fill=(0, 240, 255, 60), outline=CYAN, width=8)
    d.rounded_rectangle([70, 22, 106, 58], radius=6, fill=(0, 240, 255, 60), outline=CYAN, width=8)
    d.rounded_rectangle([22, 70, 58, 106], radius=6, fill=(0, 240, 255, 60), outline=CYAN, width=8)
    d.rounded_rectangle([70, 70, 106, 106], radius=6, fill=(0, 240, 255, 60), outline=CYAN, width=8)
    d.line([(52, 90), (68, 106)], fill=GREEN, width=12)
    d.line([(68, 106), (104, 58)], fill=GREEN, width=12)
    save_icon(img, "autostart_on")

# 8. quit.png (Power / Exit)
def make_quit():
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Arc
    d.arc([22, 22, 106, 106], start=305, end=235, fill=RED, width=10)
    # Vertical line at top
    d.line([64, 16, 64, 58], fill=RED, width=10)
    save_icon(img, "quit")

if __name__ == "__main__":
    make_logo()
    make_window()
    make_browser()
    make_folder()
    make_autostart()
    make_autostart_on()
    make_refresh()
    make_update()
    make_quit()
