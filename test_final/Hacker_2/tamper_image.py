import random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import os
import json
import argparse

# python3 tamper_image.py original_image/ tampered_images/ tampered_HL/ 20 20 sharpen tamper_log_19.json

def tamper_image(image_path, num_changes, tamper_type="random", area=None):
    image = Image.open(image_path).convert('L')
    pixels = image.load()
    width, height = image.size
    tampered_pixels = set()

    # Define the area to be tampered if provided
    if area:
        x_start, y_start, x_end, y_end = area
    else:
        x_start, y_start, x_end, y_end = 0, 0, width, height

    if tamper_type in ["random", "salt_pepper", "gaussian", "blur", "sharpen"]:
        while len(tampered_pixels) < num_changes:
            x = random.randint(x_start, x_end - 1)
            y = random.randint(y_start, y_end - 1)

            if (x, y) not in tampered_pixels:
                if tamper_type == "random":
                    current_value = pixels[x, y]
                    new_value = (current_value + random.randint(1, 50)) % 256  # Example random change
                elif tamper_type == "salt_pepper":
                    new_value = random.choice([0, 255])  # Salt and pepper noise
                elif tamper_type == "gaussian":
                    new_value = int(np.clip(pixels[x, y] + np.random.normal(0, 10), 0, 255))  # Gaussian noise
                elif tamper_type == "blur":
                    surrounding_pixels = [pixels[i, j] for i in range(max(x-1, 0), min(x+2, width)) 
                                          for j in range(max(y-1, 0), min(y+2, height))]
                    new_value = int(np.mean(surrounding_pixels))  # Simple blur by averaging surrounding pixels
                elif tamper_type == "sharpen":
                    new_value = int(np.clip(2 * pixels[x, y] - np.mean([pixels[i, j] for i in range(max(x-1, 0), min(x+2, width)) 
                                                                          for j in range(max(y-1, 0), min(y+2, height))]), 0, 255))  # Simple sharpening
                else:
                    raise ValueError("Unsupported tamper type.")
                
                pixels[x, y] = new_value
                tampered_pixels.add((x, y))

    else:
        raise ValueError("Unsupported tamper type.")
    
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
    parser.add_argument('tamper_type', type=str, choices=["random", "salt_pepper", "gaussian", "blur", "sharpen"], help="Type of tampering to apply")
    parser.add_argument('--area', type=int, nargs=4, help="Optional: Define the area to tamper as x_start y_start x_end y_end")
    parser.add_argument('log_file', type=str, help="File to save tampering log (JSON)")

    args = parser.parse_args()

    input_images = [os.path.join(args.input_folder, f) for f in os.listdir(args.input_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    random.shuffle(input_images)
    tampered_images = input_images[:args.num_images]

    tampering_log = {}

    os.makedirs(args.tampered_folder, exist_ok=True)
    os.makedirs(args.highlight_folder, exist_ok=True)

    for image_path in tampered_images:
        image_name = os.path.basename(image_path)
        tampered_output_path = os.path.join(args.tampered_folder, image_name)
        
        area = args.area if args.area else None
        tampered_image, tampered_pixels = tamper_image(image_path, args.num_changes, args.tamper_type, area)
        tampered_image.save(tampered_output_path, format='PNG')
        highlight_output_path = os.path.join(args.highlight_folder, image_name)
        save_highlighted_image(tampered_image, tampered_pixels, highlight_output_path)
        tampering_log[image_name] = tampered_pixels

    with open(args.log_file, 'w') as log_file:
        json.dump(tampering_log, log_file, indent=4)

    print(f"Tampered images saved to {args.tampered_folder}")
    print(f"Highlighted images saved to {args.highlight_folder}")
    print(f"Tampering log saved to {args.log_file}")

if __name__ == "__main__":
    main()