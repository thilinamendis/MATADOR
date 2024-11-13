import random
from PIL import Image

def tamper_image(image_path, output_path, num_changes):
    image = Image.open(image_path).convert('L')  # Convert to grayscale
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
            print(f"Pixel tampered at ({x}, {y}) with value {pixels[x, y]}")
    
    image.save(output_path, format='PNG')  # Save as PNG to preserve quality
    print(f"Image tampered and saved to {output_path}")

# Example usage
tamper_image('test.jpeg', 'tampered_image.jpeg', 20)
