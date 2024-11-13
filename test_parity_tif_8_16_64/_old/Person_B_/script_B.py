import numpy as np
from hashlib import md5
from PIL import Image
import argparse
import json
import os

# Function to divide the image into blocks
def divide_into_blocks(image, block_size):
    blocks = []
    block_positions = []
    for i in range(0, image.shape[0], block_size):
        for j in range(0, image.shape[1], block_size):
            block = image[i:i + block_size, j:j + block_size]
            blocks.append(block)
            block_positions.append((i, j))
    return blocks, block_positions

# Function to recreate the magic square
def create_magic_square(n, start_num=1):
    if n % 2 == 1:
        return create_siamese_magic_square(n, start_num)
    elif n % 4 == 0:
        return create_doubly_even_magic_square(n, start_num)
    else:
        return create_singly_even_magic_square(n, start_num)

# Magic square generation functions remain unchanged
def create_siamese_magic_square(n, start_num=1):
    magic_square = np.zeros((n, n), dtype=int)
    num = start_num
    i, j = 0, n // 2
    while num < start_num + n**2:
        magic_square[i, j] = num
        num += 1
        newi, newj = (i-1) % n, (j+1) % n
        if magic_square[newi, newj]:
            i += 1
        else:
            i, j = newi, newj
    return magic_square

def create_doubly_even_magic_square(n, start_num=1):
    magic_square = np.arange(start_num, start_num + n*n).reshape(n, n)
    indices = np.indices((n, n))
    r, c = indices[0], indices[1]
    mask = ((r % 4 == c % 4) | ((r % 4 + c % 4) == 3))
    magic_square[mask] = start_num + n*n - 1 - (magic_square[mask] - start_num)
    return magic_square

def create_singly_even_magic_square(n, start_num=1):
    half_n = n // 2
    half_magic_square = create_siamese_magic_square(half_n, start_num)
    magic_square = np.zeros((n, n), dtype=int)

    for i in range(4):
        r_offset = (i // 2) * half_n
        c_offset = (i % 2) * half_n
        if i == 0:
            magic_square[r_offset:r_offset+half_n, c_offset:c_offset+half_n] = half_magic_square
        elif i == 1:
            magic_square[r_offset:r_offset+half_n, c_offset:c_offset+half_n] = half_magic_square + 2*half_n*half_n
        elif i == 2:
            magic_square[r_offset:r_offset+half_n, c_offset+c_offset+half_n] = half_magic_square + 3*half_n*half_n
        elif i == 3:
            magic_square[r_offset:r_offset+half_n, c_offset+c_offset+half_n] = half_magic_square + half_n*half_n
    return magic_square

# Function to extract hash from 0th and 1st LSBs, leaving the last bit of 0th LSB for parity
def extract_hash_from_lsb(block, block_size):
    flat_block = block.flatten()
    extracted_hash = []
    
    hash_bits = block_size * block_size * 2 - 1  # General case: n-1 bits for hash, 1 bit for parity

    # Step 1: Extract hash from the 0th LSB (excluding the last bit for parity)
    for i in range(len(flat_block) - 1):  # Skip the last bit for parity
        if len(extracted_hash) < hash_bits:
            extracted_hash.append(str((flat_block[i] >> 0) & 1))  # Extract from 0th LSB

    # Step 2: Extract remaining hash bits from the 1st LSB
    for i in range(len(flat_block)):
        if len(extracted_hash) < hash_bits:
            extracted_hash.append(str((flat_block[i] >> 1) & 1))  # Extract from 1st LSB

    return ''.join(extracted_hash[:hash_bits])

# Function to extract the parity bit from the last bit of the 0th LSB
def extract_parity_from_lsb(block):
    flat_block = block.flatten()
    parity_bit = (flat_block[-1] >> 0) & 1  # Extract the last bit of the 0th LSB
    return str(parity_bit)

# Function to calculate and verify hash and parity
def calculate_and_verify_hash_and_parity(extracted_hash, extracted_parity, recalculated_hash, recalculated_parity):
    return extracted_hash == recalculated_hash and extracted_parity == recalculated_parity

# Main function to verify images
def main():
    parser = argparse.ArgumentParser(description="Verify images and check if they are tampered.")
    parser.add_argument('images_dir', type=str, help="Directory containing the received images")

    args = parser.parse_args()
    images_path = args.images_dir

    # Load the configuration data from the JSON file
    config_filename = "config_data.json"
    config_path = os.path.join(images_path, config_filename)

    if not os.path.exists(config_path):
        print(f"Config file {config_path} not found!")
        return

    with open(config_path, "r") as config_file:
        config = json.load(config_file)
    print(f"Loaded config data: {config}")

    block_size = config["block_size"]
    magic_constant = config["magic_constant"]
    start_num = config["start_num"]

    magic_square = create_magic_square(block_size, start_num)

    if os.path.isdir(images_path):
        image_files = [os.path.join(images_path, f) for f in os.listdir(images_path) if f.lower().endswith('.png')]
    else:
        print(f"Image directory {images_path} not found!")
        return

    for image_filename in image_files:
        print(f"\nProcessing image: {image_filename}")
        image = Image.open(image_filename).convert('L')
        image_array = np.array(image)

        blocks, block_positions = divide_into_blocks(image_array, block_size)

        for i, (block, position) in enumerate(zip(blocks, block_positions)):
            print(f"\nProcessing Block {i} at position {position}")

            msb_block = (block & 0xF8) >> 3  # Extract the upper 5 bits (MSBs)
            
            extracted_hash = extract_hash_from_lsb(block, block_size)
            extracted_parity = extract_parity_from_lsb(block)

            combined_string = ''.join(map(str, msb_block.flatten())) + format(i, '08b')
            full_hash = md5(combined_string.encode('utf-8')).hexdigest()
            recalculated_hash = bin(int(full_hash, 16))[2:].zfill(128)[:block_size * block_size * 2 - 1]
            recalculated_parity = str(recalculated_hash.count('1') % 2)

            print(f"Extracted hash: {extracted_hash}, Recalculated hash: {recalculated_hash}")
            print(f"Extracted parity: {extracted_parity}, Recalculated parity: {recalculated_parity}")

            no_tampering = calculate_and_verify_hash_and_parity(extracted_hash, extracted_parity, recalculated_hash, recalculated_parity)

            if no_tampering:
                print(f"No tampering detected at block {position}.")
            else:
                print(f"Tampering detected at block {position}.")

if __name__ == "__main__":
    main()
