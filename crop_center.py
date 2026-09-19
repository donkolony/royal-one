from PIL import Image

original = Image.open('frontend/public/assets/image_p0_i1.jpeg')
# Crop the middle section where the logo is
center_crop = original.crop((400, 600, 1800, 1400))

# Convert to grayscale and find bounding box of non-white
gray = center_crop.convert('L')
bbox = gray.point(lambda p: p < 240 and 255).getbbox()

if bbox:
    logo_only = center_crop.crop(bbox)
    
    # Make white transparent
    logo_rgba = logo_only.convert("RGBA")
    datas = logo_rgba.getdata()
    newData = []
    for item in datas:
        if item[0] > 230 and item[1] > 230 and item[2] > 230:
            newData.append((255, 255, 255, 0))
        else:
            newData.append(item)
    logo_rgba.putdata(newData)
    
    # Save the logo
    logo_rgba.save('frontend/public/rs-logo.png', "PNG")
    print(f"Saved frontend/public/rs-logo.png with size {logo_rgba.size}")
else:
    print("No bounding box found in center crop.")
