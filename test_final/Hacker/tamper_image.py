import random
from PIL import Image, ImageDraw
import os
import json
import argparse

# Usage
# python3 Hacker/tamper_image.py Hacker/original_image/ Hacker/tampered_images/ Hacker/tampered_HL/ 4 20 Hacker/tamper.json
def tamper_image(image_path, num_changes):
    image = Image.open(image_path).convert('L')
    pixels = image.load()
    
    width, height = image.size
    tampered_pixels = set()

    while len(tampered_pixels) < num_changes:
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        
        if (x, y) not in tampered_pixels:
            current_value = pixels[x, y]
            new_value = (current_value + 10) % 256  # Example change, adjust as needed
            pixels[x, y] = new_value
            tampered_pixels.add((x, y))
    
    return image, list(tampered_pixels)

def save_highlighted_image(image, tampered_pixels, output_path):
    highlighted_image = image.convert('RGB')
    draw = ImageDraw.Draw(highlighted_image)
    
    for x, y in tampered_pixels:
        draw.rectangle([x, y, x+1, y+1], outline="red")
    
    highlighted_image.save(output_path, format='PNG')

def main():
    parser = argparse.ArgumentParser(description="Tamper images in a folder.")
    parser.add_argument('input_folder', type=str, help="Folder containing the input images")
    parser.add_argument('tampered_folder', type=str, help="Folder to save the tampered images")
    parser.add_argument('highlight_folder', type=str, help="Folder to save the highlighted images")
    parser.add_argument('num_images', type=int, help="Number of images to tamper")
    parser.add_argument('num_changes', type=int, help="Number of pixels to tamper in each image")
    parser.add_argument('log_file', type=str, help="File to save tampering log (JSON)")

    args = parser.parse_args()

    input_images = [os.path.join(args.input_folder, f) for f in os.listdir(args.input_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    random.shuffle(input_images)
    tampered_images = input_images[:args.num_images]

    tampering_log = {}

    os.makedirs(args.tampered_folder, exist_ok=True)
    os.makedirs(args.highlight_folder, exist_ok=True)

    for image_path in input_images:
        image_name = os.path.basename(image_path)
        tampered_output_path = os.path.join(args.tampered_folder, image_name)
        
        if image_path in tampered_images:
            tampered_image, tampered_pixels = tamper_image(image_path, args.num_changes)
            tampered_image.save(tampered_output_path, format='PNG')
            highlight_output_path = os.path.join(args.highlight_folder, image_name)
            save_highlighted_image(tampered_image, tampered_pixels, highlight_output_path)
            tampering_log[image_name] = tampered_pixels
        else:
            original_image = Image.open(image_path)
            original_image.save(tampered_output_path, format='PNG')

    with open(args.log_file, 'w') as log_file:
        json.dump(tampering_log, log_file, indent=4)

    print(f"Tampered images saved to {args.tampered_folder}")
    print(f"Highlighted images saved to {args.highlight_folder}")
    print(f"Tampering log saved to {args.log_file}")

if __name__ == "__main__":
    main()
