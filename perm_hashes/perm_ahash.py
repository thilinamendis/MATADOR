import numpy as np
from PIL import Image
import imagehash
import random

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

def permute_magic_square(magic_square):
    n = magic_square.shape[0]
    permuted_magic_square = magic_square.copy()
    
    row_permutation = np.random.permutation(n)
    column_permutation = np.random.permutation(n)
    
    permuted_magic_square = permuted_magic_square[row_permutation, :]
    permuted_magic_square = permuted_magic_square[:, column_permutation]
    
    return permuted_magic_square

def divide_into_blocks(image, block_size):
    blocks = []
    block_positions = []
    height, width = image.shape
    for i in range(0, height, block_size):
        for j in range(0, width, block_size):
            block = image[i:i+block_size, j:j+block_size]
            if block.shape == (block_size, block_size):
                blocks.append(block)
                block_positions.append((i, j))
    return blocks, block_positions

def resize_block(block, new_size):
    image_block = Image.fromarray(block.astype(np.uint8))
    resized_block = image_block.resize((new_size, new_size), Image.ANTIALIAS)
    return np.array(resized_block)

def apply_magic_square(image, magic_square):
    block_size = magic_square.shape[0]
    ahash_size = 8
    height, width = image.shape
    transformed_image = np.zeros_like(image)

    for i in range(0, height, block_size):
        for j in range(0, width, block_size):
            block = image[i:i+block_size, j:j+block_size]
            if block.shape == (block_size, block_size):
                permuted_magic_square = permute_magic_square(magic_square)
                transformed_block = block * permuted_magic_square
                position_string = f"{i}{j}"
                block_string = ''.join(map(str, transformed_block.flatten())) + position_string
                resized_block = resize_block(transformed_block, ahash_size)
                block_hash = imagehash.average_hash(Image.fromarray(resized_block), hash_size=block_size)
                transformed_block = np.array(block_hash.hash, dtype=np.uint8) * 255
                transformed_image[i:i+block_size, j:j+block_size] = resize_block(transformed_block, block_size)

    return transformed_image

def perceptual_hash(image_path):
    image = Image.open(image_path).convert('L')
    return str(imagehash.average_hash(image))

def perceptual_hash_array(image_array):
    image = Image.fromarray(image_array)
    return str(imagehash.average_hash(image))

# Example usage
original_image_path = 'test.jpeg'
tampered_image_path = 'tampered_image.jpeg'

# Calculate aHashes
original_perceptual_hash = perceptual_hash(original_image_path)
tampered_perceptual_hash = perceptual_hash(tampered_image_path)

# Load images
original_image = Image.open(original_image_path).convert('L')
original_image_array = np.array(original_image)
tampered_image = Image.open(tampered_image_path).convert('L')
tampered_image_array = np.array(tampered_image)

# Create magic square
block_size = 3  # Use a 3x3 block size for the magic square
magic_square = create_magic_square(block_size)

# Apply magic square transformation
transformed_original_image_array = apply_magic_square(original_image_array, magic_square)
transformed_tampered_image_array = apply_magic_square(tampered_image_array, magic_square)

# Calculate aHashes for transformed images
transformed_original_perceptual_hash = perceptual_hash_array(transformed_original_image_array)
transformed_tampered_perceptual_hash = perceptual_hash_array(transformed_tampered_image_array)

# Display results
print(f"Original Perceptual Hash (aHash): {original_perceptual_hash}")
print(f"Tampered Perceptual Hash (aHash): {tampered_perceptual_hash}")
print(f"Original Magic Hash: {perceptual_hash_array(original_image_array)}")
print(f"Tampered Magic Hash: {perceptual_hash_array(tampered_image_array)}")
print(f"Transformed Original Perceptual Hash (aHash): {transformed_original_perceptual_hash}")
print(f"Transformed Tampered Perceptual Hash (aHash): {transformed_tampered_perceptual_hash}")
