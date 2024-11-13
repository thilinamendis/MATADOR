import numpy as np
import pywt
from PIL import Image
from hashlib import sha256
import random

def random_tiling(subband, tile_size):
    height, width = subband.shape
    tiles = []
    for i in range(0, height, tile_size):
        for j in range(0, width, tile_size):
            tile = subband[i:i+tile_size, j:j+tile_size]
            if tile.shape == (tile_size, tile_size):
                tiles.append(tile)
    return tiles

def calculate_statistics(tiles):
    statistics = []
    for tile in tiles:
        mean = np.mean(tile)
        variance = np.var(tile)
        statistics.append((mean, variance))
    return statistics

def randomized_rounding(statistics, key):
    random.seed(key)
    quantized_statistics = []
    for stat in statistics:
        mean, variance = stat
        q_mean = int(mean + random.random())
        q_variance = int(variance + random.random())
        quantized_statistics.append((q_mean, q_variance))
    return quantized_statistics

def encode_statistics(statistics):
    binary_str = ''
    for stat in statistics:
        q_mean, q_variance = stat
        binary_str += format(q_mean, '08b') + format(q_variance, '08b')
    return binary_str

def perceptual_hash(image_path, key):
    image = Image.open(image_path).convert('L')
    image_array = np.array(image)
    
    # Wavelet decomposition
    coeffs = pywt.wavedec2(image_array, 'haar', level=1)
    LL, (LH, HL, HH) = coeffs
    
    # Random tiling and statistics calculation
    LL_tiles = random_tiling(LL, tile_size=8)
    statistics = calculate_statistics(LL_tiles)
    
    # Randomized rounding
    quantized_statistics = randomized_rounding(statistics, key)
    
    # Encode statistics
    binary_str = encode_statistics(quantized_statistics)
    
    # Final hash using SHA-256
    hash_value = sha256(binary_str.encode('utf-8')).hexdigest()
    return hash_value

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

def divide_into_blocks(image, block_size):
    blocks = []
    block_positions = []
    for i in range(0, image.shape[0], block_size):
        for j in range(0, image.shape[1], block_size):
            block = image[i:i+block_size, j:j+block_size]
            if block.shape[0] == block_size and block.shape[1] == block_size:
                blocks.append(block)
                block_positions.append((i, j))
    return blocks, block_positions

def calculate_magic_square_hash(block, magic_square, position):
    multiplied_block = block * magic_square
    block_flattened = multiplied_block.flatten()
    block_string = ''.join(map(str, block_flattened))
    position_string = ''.join(map(str, position))
    combined_string = block_string + position_string
    return sha256(combined_string.encode('utf-8')).hexdigest()

def magic_square_hashing(image_array):
    block_size = 3
    magic_square = create_magic_square(block_size)

    blocks, block_positions = divide_into_blocks(image_array, block_size)
    hashes = [calculate_magic_square_hash(block, magic_square, position) for block, position in zip(blocks, block_positions)]

    concatenated_hashes = ''.join(hashes)
    final_hash = sha256(concatenated_hashes.encode('utf-8')).hexdigest()
    return final_hash

# Example usage
key = 12345  # Example key
original_perceptual_hash = perceptual_hash('test.jpeg', key)
tampered_perceptual_hash = perceptual_hash('tampered_image.jpeg', key)

image = Image.open('test.jpeg')
image_array = np.array(image)
original_magic_hash = magic_square_hashing(image_array)

tampered_image = Image.open('tampered_image.jpeg')
tampered_image_array = np.array(tampered_image)
tampered_magic_hash = magic_square_hashing(tampered_image_array)

print(f"Original Perceptual Hash: {original_perceptual_hash}")
print(f"Tampered Perceptual Hash: {tampered_perceptual_hash}")
print(f"Original Magic Hash: {original_magic_hash}")
print(f"Tampered Magic Hash: {tampered_magic_hash}")
