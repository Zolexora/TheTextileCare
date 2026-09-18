#!/usr/bin/env python3
"""
Generate and distribute complete brand assets for The Textile Care (TTC)
from the source branding image TTC.png.
"""
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SOURCE_IMAGE = os.path.join(REPO_ROOT, 'TTC.png')
BUILD_DIR = os.path.join(REPO_ROOT, 'scratch', 'build_assets')
os.makedirs(BUILD_DIR, exist_ok=True)

print(f"Loading source image from {SOURCE_IMAGE}...")
src = Image.open(SOURCE_IMAGE).convert('RGBA')

# 1. Precise crops
# Full logo (wave + TTC + THE TEXTILE CARE)
logo_img = src.crop((96, 354, 909, 639)) # 813 x 285
logo_path = os.path.join(BUILD_DIR, 'logo.png')
logo_img.save(logo_path)
print(f"Generated logo.png ({logo_img.size})")

# Favicon squircle icon
icon_crop = src.crop((1107, 340, 1431, 662)) # 324 x 322
# Make exact 324 x 324 square with 1px top/bottom padding
icon_324 = Image.new('RGBA', (324, 324), (0, 0, 0, 0))
icon_324.paste(icon_crop, (0, 1), icon_crop)
icon_324.save(os.path.join(BUILD_DIR, 'icon-324.png'))

# Logo mark (wave + TTC without subtitle)
mark_crop = src.crop((96, 354, 909, 550)) # 813 x 196
mark_crop.save(os.path.join(BUILD_DIR, 'logo-mark.png'))

# Wave symbol only (wave ribbons alone)
symbol_crop = src.crop((96, 354, 475, 550)) # 379 x 196
symbol_crop.save(os.path.join(BUILD_DIR, 'symbol.png'))

# 2. Dark mode / White text variants
# In TTC logo:
# - subtitle is y >= 210
# - C is x >= 600
# - second T is x in [440, 600]
# - first T is x in [275, 440] and y <= 135
# Wave is x in [0, 380] with high blue/cyan
logo_white = logo_img.copy()
lw_pix = logo_white.load()
w, h = logo_img.size

for x in range(w):
    for y in range(h):
        r, g, b, a = logo_img.getpixel((x, y))
        if a == 0:
            continue
        is_text = False
        if y >= 210:
            is_text = True
        elif x >= 440:
            is_text = True
        elif x >= 275 and y <= 135:
            is_text = True
        
        if is_text:
            lw_pix[x, y] = (255, 255, 255, a)

logo_white.save(os.path.join(BUILD_DIR, 'logo-white.png'))
print("Generated logo-white.png")

mark_white = mark_crop.copy()
mw_pix = mark_white.load()
mw_w, mw_h = mark_crop.size
for x in range(mw_w):
    for y in range(mw_h):
        r, g, b, a = mark_crop.getpixel((x, y))
        if a == 0:
            continue
        is_text = False
        if x >= 440:
            is_text = True
        elif x >= 275 and y <= 135:
            is_text = True
        if is_text:
            mw_pix[x, y] = (255, 255, 255, a)

mark_white.save(os.path.join(BUILD_DIR, 'logo-mark-white.png'))

# 3. Vector tracing via potrace for pixel-perfect SVGs
scale = 4
wave_mask = Image.new('L', (w, h), 0)
text_mask = Image.new('L', (w, h), 0)

for x in range(w):
    for y in range(h):
        r, g, b, a = logo_img.getpixel((x, y))
        if a > 80:
            if b > 150 or (b > 120 and g > 65):
                wave_mask.putpixel((x, y), a)
            else:
                text_mask.putpixel((x, y), a)

wave_4x = wave_mask.resize((w * scale, h * scale), Image.Resampling.BICUBIC)
text_4x = text_mask.resize((w * scale, h * scale), Image.Resampling.BICUBIC)

wave_pbm = os.path.join(BUILD_DIR, 'wave.pbm')
text_pbm = os.path.join(BUILD_DIR, 'text.pbm')
wave_4x.point(lambda p: 0 if p > 128 else 1, mode='1').save(wave_pbm)
text_4x.point(lambda p: 0 if p > 128 else 1, mode='1').save(text_pbm)

wave_svg_tmp = os.path.join(BUILD_DIR, 'wave_raw.svg')
text_svg_tmp = os.path.join(BUILD_DIR, 'text_raw.svg')
subprocess.run(['potrace', '-s', '-a', '1.2', '-o', wave_svg_tmp, wave_pbm], check=True)
subprocess.run(['potrace', '-s', '-a', '1.2', '-o', text_svg_tmp, text_pbm], check=True)

# Parse SVG paths
tree_wave = ET.parse(wave_svg_tmp)
tree_text = ET.parse(text_svg_tmp)

paths_wave = [p.get('d') for p in tree_wave.iter() if p.tag.endswith('path')]
paths_text = [p.get('d') for p in tree_text.iter() if p.tag.endswith('path')]

wave_paths_xml = '\n'.join([f'    <path d="{d}" fill="url(#ttcWaveGradient)" />' for d in paths_wave])
text_paths_xml = '\n'.join([f'    <path d="{d}" fill="#062B5F" />' for d in paths_text])
text_white_paths_xml = '\n'.join([f'    <path d="{d}" fill="#FFFFFF" />' for d in paths_text])

# Assemble full logo.svg
logo_svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 813 285" width="813" height="285">
  <defs>
    <linearGradient id="ttcWaveGradient" x1="0%" y1="100%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#00A3FF" />
      <stop offset="40%" stop-color="#0084FF" />
      <stop offset="100%" stop-color="#0052CC" />
    </linearGradient>
  </defs>
  <g id="ttc-logo" transform="translate(0, 285) scale(0.025, -0.025)" stroke="none">
{wave_paths_xml}
{text_paths_xml}
  </g>
</svg>'''

logo_svg_path = os.path.join(BUILD_DIR, 'logo.svg')
with open(logo_svg_path, 'w') as f:
    f.write(logo_svg_content)

# Assemble logo-white.svg
logo_white_svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 813 285" width="813" height="285">
  <defs>
    <linearGradient id="ttcWaveGradient" x1="0%" y1="100%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#00A3FF" />
      <stop offset="40%" stop-color="#0084FF" />
      <stop offset="100%" stop-color="#0052CC" />
    </linearGradient>
  </defs>
  <g id="ttc-logo-white" transform="translate(0, 285) scale(0.025, -0.025)" stroke="none">
{wave_paths_xml}
{text_white_paths_xml}
  </g>
</svg>'''

logo_white_svg_path = os.path.join(BUILD_DIR, 'logo-white.svg')
with open(logo_white_svg_path, 'w') as f:
    f.write(logo_white_svg_content)

# Standalone wave symbol SVG
symbol_svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 380 196" width="380" height="196">
  <defs>
    <linearGradient id="ttcWaveGradient" x1="0%" y1="100%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#00A3FF" />
      <stop offset="40%" stop-color="#0084FF" />
      <stop offset="100%" stop-color="#0052CC" />
    </linearGradient>
  </defs>
  <g id="ttc-symbol" transform="translate(0, 285) scale(0.025, -0.025)" stroke="none">
{wave_paths_xml}
  </g>
</svg>'''

symbol_svg_path = os.path.join(BUILD_DIR, 'symbol.svg')
with open(symbol_svg_path, 'w') as f:
    f.write(symbol_svg_content)

# 4. Icon SVG tracing (White symbol inside squircle)
iw, ih = icon_324.size
symbol_icon_mask = Image.new('L', (iw, ih), 0)
for x in range(iw):
    for y in range(ih):
        r, g, b, a = icon_324.getpixel((x, y))
        if a > 100 and r > 180 and g > 180 and b > 180:
            symbol_icon_mask.putpixel((x, y), 255)

symbol_icon_4x = symbol_icon_mask.resize((iw * scale, ih * scale), Image.Resampling.BICUBIC)
symbol_icon_pbm = os.path.join(BUILD_DIR, 'symbol_icon.pbm')
symbol_icon_4x.point(lambda p: 0 if p > 128 else 1, mode='1').save(symbol_icon_pbm)

symbol_icon_svg_tmp = os.path.join(BUILD_DIR, 'symbol_icon_raw.svg')
subprocess.run(['potrace', '-s', '-a', '1.2', '-o', symbol_icon_svg_tmp, symbol_icon_pbm], check=True)

tree_sym_icon = ET.parse(symbol_icon_svg_tmp)
paths_sym_icon = [p.get('d') for p in tree_sym_icon.iter() if p.tag.endswith('path')]
sym_icon_paths_xml = '\n'.join([f'    <path d="{d}" fill="#FFFFFF" />' for d in paths_sym_icon])

icon_svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 324 324" width="324" height="324">
  <defs>
    <linearGradient id="ttcIconGradient" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#0887F5" />
      <stop offset="100%" stop-color="#0C3ACF" />
    </linearGradient>
  </defs>
  <rect width="324" height="324" rx="72" fill="url(#ttcIconGradient)" />
  <g id="ttc-icon-symbol" transform="translate(0, 324) scale(0.025, -0.025)" stroke="none">
{sym_icon_paths_xml}
  </g>
</svg>'''

icon_svg_path = os.path.join(BUILD_DIR, 'icon.svg')
with open(icon_svg_path, 'w') as f:
    f.write(icon_svg_content)

# White symbol alone SVG
symbol_white_svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 324 324" width="324" height="324">
  <g id="ttc-symbol-white" transform="translate(0, 324) scale(0.025, -0.025)" stroke="none">
{sym_icon_paths_xml}
  </g>
</svg>'''
with open(os.path.join(BUILD_DIR, 'symbol-white.svg'), 'w') as f:
    f.write(symbol_white_svg_content)

print("Generated SVGs: logo.svg, logo-white.svg, symbol.svg, icon.svg, symbol-white.svg")

# 5. Render high-resolution PNGs from SVG using rsvg-convert
def render_svg_to_png(svg_in, png_out, width, height, bg=None):
    cmd = ['rsvg-convert', '-w', str(width), '-h', str(height), svg_in, '-o', png_out]
    if bg:
        cmd.extend(['-b', bg])
    subprocess.run(cmd, check=True)

# Master Icon PNGs: 1024x1024, 512x512, 192x192, 180x180, 32x32, 16x16
icon_1024 = os.path.join(BUILD_DIR, 'icon.png')
render_svg_to_png(icon_svg_path, icon_1024, 1024, 1024)
render_svg_to_png(icon_svg_path, os.path.join(BUILD_DIR, 'icon-512.png'), 512, 512)
render_svg_to_png(icon_svg_path, os.path.join(BUILD_DIR, 'android-chrome-512x512.png'), 512, 512)
render_svg_to_png(icon_svg_path, os.path.join(BUILD_DIR, 'android-chrome-192x192.png'), 192, 192)
render_svg_to_png(icon_svg_path, os.path.join(BUILD_DIR, 'apple-touch-icon.png'), 180, 180)
render_svg_to_png(icon_svg_path, os.path.join(BUILD_DIR, 'favicon-32x32.png'), 32, 32)
render_svg_to_png(icon_svg_path, os.path.join(BUILD_DIR, 'favicon-16x16.png'), 16, 16)
render_svg_to_png(icon_svg_path, os.path.join(BUILD_DIR, 'favicon.png'), 32, 32)

# Generate multi-res favicon.ico (16, 32, 48)
img_16 = Image.open(os.path.join(BUILD_DIR, 'favicon-16x16.png'))
img_32 = Image.open(os.path.join(BUILD_DIR, 'favicon-32x32.png'))
img_48 = Image.open(os.path.join(BUILD_DIR, 'apple-touch-icon.png')).resize((48, 48), Image.Resampling.LANCZOS)
ico_path = os.path.join(BUILD_DIR, 'favicon.ico')
img_48.save(ico_path, format='ICO', sizes=[(16, 16), (32, 32), (48, 48)], append_images=[img_32, img_16])
print("Generated favicon.ico with multi-resolutions (16x16, 32x32, 48x48)")

# Adaptive icon foreground for Android (432x432 with transparent background and centered white wave symbol)
render_svg_to_png(os.path.join(BUILD_DIR, 'symbol-white.svg'), os.path.join(BUILD_DIR, 'adaptive-icon.png'), 432, 432)

# Mobile Splash screen (1242 x 2436, deep navy brand background #062B5F, centered white logo)
splash = Image.new('RGBA', (1242, 2436), (6, 43, 95, 255))
# Render large white logo (e.g. 700px wide)
splash_logo_tmp = os.path.join(BUILD_DIR, 'splash_logo_tmp.png')
render_svg_to_png(logo_white_svg_path, splash_logo_tmp, 700, int(700 * 285 / 813))
splash_logo = Image.open(splash_logo_tmp)
splash_x = (1242 - splash_logo.width) // 2
splash_y = (2436 - splash_logo.height) // 2
splash.paste(splash_logo, (splash_x, splash_y), splash_logo)
splash.save(os.path.join(BUILD_DIR, 'splash.png'))
print("Generated splash.png (1242x2436)")

# Generate site.webmanifest
webmanifest_content = '''{
  "name": "The Textile Care",
  "short_name": "TTC",
  "icons": [
    {
      "src": "/android-chrome-192x192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/android-chrome-512x512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ],
  "theme_color": "#062b5f",
  "background_color": "#ffffff",
  "display": "standalone"
}
'''
with open(os.path.join(BUILD_DIR, 'site.webmanifest'), 'w') as f:
    f.write(webmanifest_content)

# 6. Copy assets to packages/branding/assets
branding_assets_dir = os.path.join(REPO_ROOT, 'packages', 'branding', 'assets')
os.makedirs(branding_assets_dir, exist_ok=True)

all_assets = [
    'logo.png', 'logo-white.png', 'logo-mark.png', 'logo-mark-white.png',
    'symbol.png', 'icon.png', 'icon-512.png', 'apple-touch-icon.png',
    'favicon-32x32.png', 'favicon-16x16.png', 'favicon.png', 'favicon.ico',
    'android-chrome-192x192.png', 'android-chrome-512x512.png',
    'adaptive-icon.png', 'splash.png',
    'logo.svg', 'logo-white.svg', 'symbol.svg', 'icon.svg',
    'site.webmanifest'
]

for filename in all_assets:
    src_file = os.path.join(BUILD_DIR, filename)
    if os.path.exists(src_file):
        shutil.copy2(src_file, os.path.join(branding_assets_dir, filename))
print(f"Copied all master assets to {branding_assets_dir}")

# 7. Distribute to Web apps
web_apps = ['admin-web', 'marketplace-web', 'seller-web']
for app_name in web_apps:
    public_dir = os.path.join(REPO_ROOT, 'apps', app_name, 'public')
    os.makedirs(public_dir, exist_ok=True)
    assets_sub = os.path.join(public_dir, 'assets')
    os.makedirs(assets_sub, exist_ok=True)
    
    for filename in all_assets:
        src_file = os.path.join(BUILD_DIR, filename)
        if os.path.exists(src_file):
            shutil.copy2(src_file, os.path.join(public_dir, filename))
            shutil.copy2(src_file, os.path.join(assets_sub, filename))
    print(f"Distributed assets to apps/{app_name}/public")

# 8. Distribute to Mobile apps
mobile_apps = ['driver-mobile', 'marketplace-mobile', 'seller-mobile']
for app_name in mobile_apps:
    mobile_assets_dir = os.path.join(REPO_ROOT, 'apps', app_name, 'assets')
    os.makedirs(mobile_assets_dir, exist_ok=True)
    for filename in all_assets:
        src_file = os.path.join(BUILD_DIR, filename)
        if os.path.exists(src_file):
            shutil.copy2(src_file, os.path.join(mobile_assets_dir, filename))
    print(f"Distributed assets to apps/{app_name}/assets")

print("\n=== All TTC Brand Assets Successfully Generated and Distributed! ===")
