import numpy as np
from hashlib import sha256
from cryptography.fernet import Fernet
from PIL import Image
import argparse
import json
import os
import time

# Usage
# python3 Person_A/script_A.py Person_A/images

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

# Function to calculate a hash for a block using magic square multiplication and block position
def calculate_magic_square_hash(block, magic_square, position):
    multiplied_block = block * magic_square
    block_flattened = multiplied_block.flatten()
    block_string = ''.join(map(str, block_flattened))
    position_string = ''.join(map(str, position))
    combined_string = block_string + position_string
    return sha256(combined_string.encode('utf-8')).hexdigest()

# Function to hash a pair of values
def hash_pair(left, right):
    return sha256((left + right).encode('utf-8')).hexdigest()

# Function to build the Merkle tree and return the root hash and path proofs
def build_merkle_tree_with_proofs(hashes):
    tree = [hashes]
    current_level = hashes
    while len(current_level) > 1:
        new_level = []
        for i in range(0, len(current_level), 2):
            left = current_level[i]
            right = current_level[i + 1] if i + 1 < len(current_level) else current_level[i]
            new_level.append(hash_pair(left, right))
        tree.append(new_level)
        current_level = new_level
    root_hash = tree[-1][0]
    path_proofs = generate_path_proofs(tree)
    return root_hash, path_proofs

# Function to generate path proofs for each block
def generate_path_proofs(tree):
    path_proofs = []
    num_levels = len(tree)
    num_blocks = len(tree[0])

    for i in range(num_blocks):
        proof = []
        index = i
        for level in range(num_levels - 1):
            sibling_index = index + 1 if index % 2 == 0 else index - 1
            if sibling_index < len(tree[level]):
                proof.append(tree[level][sibling_index])
            index //= 2
        path_proofs.append(proof)
    return path_proofs

# Function to securely store the root hash
def store_root_hash(root_hash, key_file, storage_file):
    # Ensure key is only generated once
    if not os.path.exists(key_file):
        key = Fernet.generate_key()
        with open(key_file, "wb") as key_file:
            key_file.write(key)
    else:
        with open(key_file, "rb") as key_file:
            key = key_file.read()

    cipher_suite = Fernet(key)
    encrypted_root_hash = cipher_suite.encrypt(root_hash.encode())
    
    os.makedirs(os.path.dirname(storage_file), exist_ok=True)
    with open(storage_file, "wb") as file:
        file.write(encrypted_root_hash)
    
    print(f"Root hash stored securely at {storage_file}.")

# Improved magic square generation functions
def create_magic_square(n, start_num=1):
    if n < 3:
        raise ValueError("Block size must be at least 3 to form a valid magic square.")
    
    if n % 2 == 1:
        return create_siamese_magic_square(n, start_num)
    elif n % 4 == 0:
        return create_doubly_even_magic_square(n, start_num)
    else:
        return create_singly_even_magic_square(n, start_num)

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

    # Positioning smaller squares in quadrants
    for i in range(4):
        r_offset = (i // 2) * half_n
        c_offset = (i % 2) * half_n
        if i == 0:
            # Top-left quadrant
            magic_square[r_offset:r_offset+half_n, c_offset:c_offset+half_n] = half_magic_square
        elif i == 1:
            # Top-right quadrant
            magic_square[r_offset:r_offset+half_n, c_offset:c_offset+half_n] = half_magic_square + 2*half_n*half_n
        elif i == 2:
            # Bottom-left quadrant
            magic_square[r_offset:r_offset+half_n, c_offset:c_offset+half_n] = half_magic_square + 3*half_n*half_n
        elif i == 3:
            # Bottom-right quadrant
            magic_square[r_offset:r_offset+half_n, c_offset:c_offset+half_n] = half_magic_square + half_n*half_n

    # Swapping values to make it magic
    k = (n - 2) // 4
    for i in range(half_n):
        for j in range(k):
            if j == k - 1 and i == k:
                # Do nothing
                continue
            # Swap elements in top-left and bottom-left quadrants
            magic_square[i, j], magic_square[i + half_n, j] = magic_square[i + half_n, j], magic_square[i, j]

    for i in range(half_n):
        for j in range(n - k, n):
            # Swap elements in top-right and bottom-right quadrants
            magic_square[i, j], magic_square[i + half_n, j] = magic_square[i + half_n, j], magic_square[i, j]

    return magic_square

def generate_possible_magic_numbers(n, start_nums):
    magic_numbers = []
    for start_num in start_nums:
        magic_square = create_magic_square(n, start_num)
        magic_number = np.sum(magic_square[0])
        magic_numbers.append(magic_number)
    return magic_numbers

def get_positive_integer(prompt):
    while True:
        try:
            value = int(input(prompt))
            if value <= 0:
                raise ValueError
            return value
        except ValueError:
            print("Invalid input. Please enter a positive integer.")

# Function to add padding to the image if its dimensions are not multiples of the block size
def add_padding(image, block_size):
    h, w = image.shape
    new_h = (h + block_size - 1) // block_size * block_size
    new_w = (w + block_size - 1) // block_size * block_size
    padded_image = np.zeros((new_h, new_w), dtype=image.dtype)
    padded_image[:h, :w] = image
    return padded_image

# Main function to handle user inputs and process the images
def main():
    parser = argparse.ArgumentParser(description="Process images and generate block hashes.")
    parser.add_argument('images_path', type=str, help="Directory containing the input images or a single image file")

    args = parser.parse_args()
    images_path = args.images_path

    while True:
        block_size = get_positive_integer("Enter the block size (positive integer, at least 3): ")
        if block_size >= 3:
            break
        else:
            print("Error: Block size must be at least 3 to form a valid magic square.")
    
    start_nums = list(range(1, 12))  # You can adjust this range as needed
    possible_magic_numbers = generate_possible_magic_numbers(block_size, start_nums)
    print(f"Suggested magic numbers for a {block_size}x{block_size} grid based on different starting numbers: {possible_magic_numbers}")

    while True:
        try:
            magic_number = get_positive_integer("Enter the magic number: ")
            if magic_number not in possible_magic_numbers:
                raise ValueError(f"Magic number must be one of the suggested values: {possible_magic_numbers}")
            break
        except ValueError as e:
            print(f"Error: {e}")

    start_num_index = possible_magic_numbers.index(magic_number)
    start_num = start_nums[start_num_index]

    config = {
        "block_size": block_size,
        "magic_constant": magic_number,
        "start_num": start_num  # Add start_num to the config
    }

    config_filename = "config.json"
    config_path = os.path.join("Person_A/config", config_filename)
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w") as config_file:
        json.dump(config, config_file)

    # Ensure the encryption key file is created only once
    key_filename = "encryption_key.txt"
    key_path = os.path.join("Person_A/key", key_filename)
    
    if not os.path.exists(key_path):
        key = Fernet.generate_key()
        os.makedirs(os.path.dirname(key_path), exist_ok=True)
        with open(key_path, "wb") as key_file:
            key_file.write(key)

    if os.path.isdir(images_path):
        image_files = [os.path.join(images_path, f) for f in os.listdir(images_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    else:
        image_files = [images_path]

    total_images = 0
    total_processing_time = 0
    overall_start_time = time.time()

    for image_filename in image_files:
        image_path = image_filename

        # Load the image
        print("\n" + "="*50)
        print(f"\nProcessing for the image --> {os.path.basename(image_filename)}.")
        print("\n" + "="*50)
        total_images += 1
        total_start_time = time.time()
        start_time = time.time()
        image = Image.open(image_path).convert('L')
        image = np.array(image)
        if image.shape[0] % block_size != 0 or image.shape[1] % block_size != 0:
            print(f"Image dimensions of {os.path.basename(image_filename)} are not multiples of the block size. Adding padding...")
            image = add_padding(image, block_size)
        end_time = time.time()

        print("\n" + "="*50)
        print(f"\nProcessing for the image --> {os.path.basename(image_filename)}.")
        print("\n" + "="*50)
        print(f"Image dimensions: {image.shape}")
        print(f"Block size: {block_size}")
        print(f"\nTime taken to load and pad image: {end_time - start_time} seconds")

        # Create the magic square
        start_time = time.time()
        magic_square = create_magic_square(block_size, start_num)
        end_time = time.time()
        print(f"\nTime taken to create magic square: {end_time - start_time} seconds")
        print(f"Magic Square:\n{magic_square}")
        
        # Divide the image into blocks
        start_time = time.time()
        blocks, block_positions = divide_into_blocks(image, block_size)
        end_time = time.time()
        print(f"\nTime taken to divide image into blocks: {end_time - start_time} seconds")
        print(f"Number of blocks: {len(blocks)}")
        
        # Calculate the hashes for each block using magic square and block position
        start_time = time.time()
        original_hashes = [calculate_magic_square_hash(block, magic_square, position) for block, position in zip(blocks, block_positions)]
        end_time = time.time()
        print(f"\nTime taken to calculate hashes for blocks: {end_time - start_time} seconds")
        
        # Build Merkle tree and store the root hash and path proofs
        start_time = time.time()
        original_root_hash, path_proofs = build_merkle_tree_with_proofs(original_hashes)
        end_time = time.time()
        print(f"\nTime taken to build Merkle tree: {end_time - start_time} seconds")
        
        # Store the root hash securely
        start_time = time.time()
        root_hash_filename = f"root_hash_storage_{os.path.basename(image_filename)}.txt"
        root_hash_path = os.path.join("Person_A/hashes", root_hash_filename)
        store_root_hash(original_root_hash, key_path, root_hash_path)
        end_time = time.time()
        print(f"\nTime taken to store root hash: {end_time - start_time} seconds")
        
        # Save path proofs
        start_time = time.time()
        path_proofs_filename = f"path_proofs_{os.path.basename(image_filename)}.json"
        path_proofs_path = os.path.join("Person_A/hashes", path_proofs_filename)
        with open(path_proofs_path, "w") as file:
            json.dump(original_hashes, file)
        end_time = time.time()
        print(f"\nTime taken to save path proofs: {end_time - start_time} seconds")
        
        print(f"\nRoot hash and path proofs for {os.path.basename(image_filename)} stored successfully.")
        print("Processing completed successfully.")
        total_end_time = time.time()
        print(f"\nTotal time taken for processing image {os.path.basename(image_filename)} is : {total_end_time - total_start_time} seconds")
        print("\n" + "*"*100)

    overall_end_time = time.time()

    total_processing_time = overall_end_time - overall_start_time

    print(f"\nTotal time taken for processing all images is : {overall_end_time - overall_start_time} seconds")
    print(f"Total number of images processed: {total_images}")
    print(f"Average processing time per image: {total_processing_time / total_images} seconds")

if __name__ == "__main__":
    main()
