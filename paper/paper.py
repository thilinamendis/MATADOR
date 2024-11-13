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

# Example usage
key = 12345  # Example key
original_hash = perceptual_hash('test.jpeg', key)
tampered_hash = perceptual_hash('tampered_image.jpeg', key)
print(f"Original Hash: {original_hash}")
print(f"Tampered Hash: {tampered_hash}")
