#!/usr/bin/env python3

import numpy as np
from hashlib import sha256
from cryptography.fernet import Fernet
from PIL import Image
import argparse
import json

# Constants
BLOCK_SIZE = 3
MAGIC_CONSTANT = 15

# Function to divide the image into blocks and keep track of block positions
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
            right = current_level[i+1] if i+1 < len(current_level) else current_level[i]
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
def store_root_hash(root_hash, key_file="encryption_key.txt", storage_file="root_hash_storage.txt"):
    key = Fernet.generate_key()
    cipher_suite = Fernet(key)
    encrypted_root_hash = cipher_suite.encrypt(root_hash.encode())
    
    with open(storage_file, "wb") as file:
        file.write(encrypted_root_hash)
    
    with open(key_file, "wb") as key_file:
        key_file.write(key)
    print("Root hash stored securely.")

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

# Main function to handle user inputs and process the image
def main():
    parser = argparse.ArgumentParser(description="Process an image and generate block hashes.")
    parser.add_argument('image_path', type=str, help="Path to the input image")

    args = parser.parse_args()

    # Load the image
    image = Image.open(args.image_path).convert('L')
    image = np.array(image)

    # Check if image dimensions are multiples of block size
    if image.shape[0] % BLOCK_SIZE != 0 or image.shape[1] % BLOCK_SIZE != 0:
        print("Error: Image dimensions must be multiples of the block size.")
        return
    
    print(f"Image dimensions: {image.shape}")
    print(f"Block size: {BLOCK_SIZE}")
    
    # Create the magic square
    magic_square = create_magic_square(BLOCK_SIZE)
    print(f"Magic Square:\n{magic_square}")
    
    # Divide the image into blocks
    blocks, block_positions = divide_into_blocks(image, BLOCK_SIZE)
    print(f"Number of blocks: {len(blocks)}")
    
    # Calculate the hashes for each block using magic square and block position
    original_hashes = [calculate_magic_square_hash(block, magic_square, position) for block, position in zip(blocks, block_positions)]
    
    # Build Merkle tree and store the root hash and path proofs
    original_root_hash, path_proofs = build_merkle_tree_with_proofs(original_hashes)
    
    # Store the root hash securely
    store_root_hash(original_root_hash)
    
    # Save path proofs
    with open("path_proofs_a.json", "w") as file:
        json.dump(path_proofs, file)
    
    print("Root hash and path proofs stored successfully.")
    print("Processing completed successfully.")

if __name__ == "__main__":
    main()
