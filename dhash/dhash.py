import numpy as np
from hashlib import sha256
from PIL import Image
import imagehash

# Constants
BLOCK_SIZE = 3

# Function to calculate the difference hash of an image
def difference_hash(image, hash_size=8):
    return imagehash.dhash(image, hash_size=hash_size)

# Function to divide the image into blocks and keep track of block positions
def divide_into_blocks(image, block_size):
    blocks = []
    block_positions = []
    for i in range(0, image.shape[0], block_size):
        for j in range(0, image.shape[1], block_size):
            block = image[i:i+block_size, j:j+block_size]
            blocks.append(block)
            block_positions.append((i, j))
    return blocks, block_positions

# Function to create a magic square of a given size
def create_magic_square(n):
    magic_square = np.zeros((n, n), dtype=int)
    num = 1
    i, j = 0, n // 2
    while num <= n**2:
        magic_square[i, j] = num
        num += 1
        newi, newj = (i-1) % n, (j+1) % n
        if magic_square[newi, newj]:
            i += 1
        else:
            i, j = newi, newj
    return magic_square

# Function to apply the magic square transformation considering block location
def apply_magic_square(image, magic_square):
    pixels = np.array(image)
    block_size = magic_square.shape[0]
    transformed = np.zeros_like(pixels, dtype=np.uint8)

    for i in range(0, pixels.shape[0] - block_size + 1, block_size):
        for j in range(0, pixels.shape[1] - block_size + 1, block_size):
            block = pixels[i:i+block_size, j:j+block_size]
            transformed_block = block * magic_square
            position_string = f"{i}{j}"
            block_string = ''.join(map(str, transformed_block.flatten())) + position_string
            block_hash = sha256(block_string.encode('utf-8')).hexdigest()
            transformed_block = np.array([int(block_hash[k:k+2], 16) for k in range(0, len(block_hash), 2)])
            transformed_block = transformed_block[:block_size**2].reshape(block_size, block_size)
            transformed[i:i+block_size, j:j+block_size] = transformed_block

    return Image.fromarray(transformed)

# Main function to handle user inputs and verify the image
def main():
    # Load the images
    original_image = Image.open('test.jpeg').convert('L')
    tampered_image = Image.open('tampered_image.jpeg').convert('L')

    # Calculate the difference hash for the original and tampered images
    original_hash_dhash = difference_hash(original_image)
    tampered_hash_dhash = difference_hash(tampered_image)
    
    print(f"Original Hash with dHash: {original_hash_dhash}")
    print(f"Tampered Hash with dHash: {tampered_hash_dhash}")
    
    # Define a magic square
    magic_square = create_magic_square(BLOCK_SIZE)
    
    # Apply the magic square transformation
    transformed_original_image = apply_magic_square(original_image, magic_square)
    transformed_tampered_image = apply_magic_square(tampered_image, magic_square)
    
    # Calculate the difference hash for the transformed images
    transformed_original_hash_dhash = difference_hash(transformed_original_image)
    transformed_tampered_hash_dhash = difference_hash(transformed_tampered_image)
    
    print(f"Original Hash with dHash + Magic Square: {transformed_original_hash_dhash}")
    print(f"Tampered Hash with dHash + Magic Square: {transformed_tampered_hash_dhash}")
    
    # Compare the hashes
    if original_hash_dhash == tampered_hash_dhash:
        print("Hashes with dHash match. No tampering detected.")
    else:
        print("Hashes with dHash do not match. Tampering detected.")
    
    if transformed_original_hash_dhash == transformed_tampered_hash_dhash:
        print("Hashes with dHash + Magic Square match. No tampering detected.")
    else:
        print("Hashes with dHash + Magic Square do not match. Tampering detected.")

if __name__ == "__main__":
    main()
