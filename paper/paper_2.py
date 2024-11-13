import numpy as np
import pywt
from PIL import Image
import random
from scipy.special import comb
import hashlib


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

def reed_muller_encode(binary_str):
    # Reed-Muller (1, m) encoding
    # This is a simplified version for demonstration purposes
    m = 3  # Choose a small m for simplicity
    n = 2 ** m
    encoded_str = ''
    
    for i in range(0, len(binary_str), n):
        block = binary_str[i:i+n]
        if len(block) < n:
            block = block.ljust(n, '0')  # Pad block to length n
        encoded_block = reed_muller_encode_block(block, m)
        encoded_str += ''.join(map(str, encoded_block))
    
    return encoded_str

def reed_muller_encode_block(block, m):
    n = 2 ** m
    k = m + 1
    block = [int(b) for b in block]
    
    # Generate the generator matrix for RM(1, m)
    G = np.zeros((k, n), dtype=int)
    G[0, :] = 1
    for i in range(m):
        G[i+1, :] = np.tile(np.repeat([0, 1], 2**(m-i-1)), 2**i)
    
    encoded_block = np.dot(block[:k], G) % 2
    return encoded_block

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
    
    # Final hash using Reed-Muller encoding
    final_hash = reed_muller_encode(binary_str)
    return final_hash

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

def convert_to_checksum(answer_string):
    checksum = hashlib.sha256(answer_string.encode()).hexdigest()
    return checksum

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

def magic_square_transform(image_array, magic_square):
    block_size = magic_square.shape[0]
    blocks, block_positions = divide_into_blocks(image_array, block_size)
    transformed_blocks = []
    for block in blocks:
        transformed_block = block * magic_square
        transformed_blocks.append(transformed_block)
    return transformed_blocks, block_positions

def perceptual_hash_with_magic(image_path, key, magic_square):
    image = Image.open(image_path).convert('L')
    image_array = np.array(image)
    
    # Apply magic square transformation
    transformed_blocks, block_positions = magic_square_transform(image_array, magic_square)
    
    # Concatenate transformed blocks into one array
    transformed_image_array = np.block([
        [transformed_blocks[i * (image_array.shape[1] // magic_square.shape[1]) + j] 
         for j in range(image_array.shape[1] // magic_square.shape[1])] 
        for i in range(image_array.shape[0] // magic_square.shape[0])
    ])
    
    # Wavelet decomposition
    coeffs = pywt.wavedec2(transformed_image_array, 'haar', level=1)
    LL, (LH, HL, HH) = coeffs
    
    # Random tiling and statistics calculation
    LL_tiles = random_tiling(LL, tile_size=8)
    statistics = calculate_statistics(LL_tiles)
    
    # Randomized rounding
    quantized_statistics = randomized_rounding(statistics, key)
    
    # Encode statistics
    binary_str = encode_statistics(quantized_statistics)
    
    # Final hash using Reed-Muller encoding
    final_hash = reed_muller_encode(binary_str)
    return final_hash

# Example usage
key = 12345  # Example key
magic_square_size = 3
magic_square = create_magic_square(magic_square_size)

original_perceptual_hash = perceptual_hash('test.jpeg', key)
tampered_perceptual_hash = perceptual_hash('tampered_image.jpeg', key)

original_perceptual_hash_magic = perceptual_hash_with_magic('test.jpeg', key, magic_square)
tampered_perceptual_hash_magic = perceptual_hash_with_magic('tampered_image.jpeg', key, magic_square)

print(f"Original Perceptual Hash: {original_perceptual_hash}")
print(f"Tampered Perceptual Hash: {tampered_perceptual_hash}")
print(f"Original Perceptual Hash with Magic: {original_perceptual_hash_magic}")
print(f"Tampered Perceptual Hash with Magic: {tampered_perceptual_hash_magic}")

# New print statements for checksums
print(f"Original Perceptual Hash Checksum: {convert_to_checksum(original_perceptual_hash)}")
print(f"Tampered Perceptual Hash Checksum: {convert_to_checksum(tampered_perceptual_hash)}")
print(f"Original Perceptual Hash with Magic Checksum: {convert_to_checksum(original_perceptual_hash_magic)}")
print(f"Tampered Perceptual Hash with Magic Checksum: {convert_to_checksum(tampered_perceptual_hash_magic)}")
