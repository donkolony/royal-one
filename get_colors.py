from PIL import Image
from collections import Counter
import sys

def rgb_to_hex(rgb):
    return '%02x%02x%02x' % rgb

img = Image.open(sys.argv[1])
img = img.convert('RGB')
pixels = list(img.getdata())

# Filter out white/near-white pixels
filtered = [p for p in pixels if not (p[0] > 240 and p[1] > 240 and p[2] > 240)]

# Count colors
counts = Counter(filtered)
most_common = counts.most_common(10)

print("Most common non-white colors:")
for color, count in most_common:
    print(f"#{rgb_to_hex(color)} (RGB: {color}) - Count: {count}")
