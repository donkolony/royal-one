from PIL import Image, ImageFilter

img = Image.open('frontend/public/assets/image_p0_i1.jpeg').convert('L')
# Blur to remove noise
blurred = img.filter(ImageFilter.GaussianBlur(radius=2))
# Strict threshold: only pixels darker than 200 (mostly text/logo)
bbox = blurred.point(lambda p: p < 220 and 255).getbbox()
print(f'Strict bounding box: {bbox}')

if bbox:
    original = Image.open('frontend/public/assets/image_p0_i1.jpeg')
    cropped = original.crop(bbox)
    
    pad = 50
    padded = Image.new('RGBA', (cropped.width + pad*2, cropped.height + pad*2), (255, 255, 255, 0))
    # Make white background transparent
    cropped_rgba = cropped.convert("RGBA")
    datas = cropped_rgba.getdata()
    newData = []
    for item in datas:
        # change all white (also shades of whites)
        if item[0] > 230 and item[1] > 230 and item[2] > 230:
            newData.append((255, 255, 255, 0))
        else:
            newData.append(item)
    cropped_rgba.putdata(newData)
    
    padded.paste(cropped_rgba, (pad, pad))
    padded.save('frontend/public/logo-transparent.png', "PNG")
    print("Saved frontend/public/logo-transparent.png")
