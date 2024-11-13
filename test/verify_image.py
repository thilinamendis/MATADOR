from PIL import Image

def verify_image(original_image_path, tampered_image_path):
    original_image = Image.open(original_image_path).convert('L')  # Convert to grayscale
    tampered_image = Image.open(tampered_image_path).convert('L')  # Convert to grayscale
    
    original_pixels = original_image.load()
    tampered_pixels = tampered_image.load()
    
    width, height = original_image.size
    tampered_count = 0

    for x in range(width):
        for y in range(height):
            if original_pixels[x, y] != tampered_pixels[x, y]:
                tampered_count += 1
                print(f"Pixel tampered at ({x}, {y}): Original {original_pixels[x, y]}, Tampered {tampered_pixels[x, y]}")
    
    print(f"Total tampered pixels detected: {tampered_count}")

# Example usage
verify_image('test.jpeg', 'tampered_image.jpeg')
