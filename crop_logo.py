from PIL import Image

def find_content_bbox(img_path):
    img = Image.open(img_path).convert('L') # Convert to grayscale
    # Threshold to find non-white pixels
    # White is 255. Let's say anything < 240 is content
    threshold = 240
    bbox = img.point(lambda p: p < threshold and 255).getbbox()
    return bbox

bbox = find_content_bbox('frontend/public/assets/image_p0_i1.jpeg')
print(f'Content bounding box: {bbox}')

if bbox:
    img = Image.open('frontend/public/assets/image_p0_i1.jpeg')
    cropped = img.crop(bbox)
    
    # Add a little padding
    pad = 20
    padded = Image.new(img.mode, (cropped.width + pad*2, cropped.height + pad*2), (255, 255, 255))
    padded.paste(cropped, (pad, pad))
    
    padded.save('frontend/public/assets/logo.png')
    print("Saved logo.png")
