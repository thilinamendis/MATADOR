import numpy as np
from hashlib import sha256
from cryptography.fernet import Fernet
from PIL import Image, ImageDraw
import argparse
import json

# Constants
BLOCK_SIZE = 3
MAGIC_CONSTANT = 15  # The sum of the numbers you provided

# Function to divide the image into blocks and keep track of block positions
def divide_into_blocks(image, block_size):
    blocks = []
    block_positions = []
    for i in range(0, image.shape[0] - block_size + 1, block_size):
        for j in range(0, image.shape[1] - block_size + 1, block_size):
            block = image[i:i+block_size, j:j+block_size]
            if block.shape[0] == block_size and block.shape[1] == block_size:  # Ensure the block is of the correct size
                blocks.append(block)
                block_positions.append((i, j))
    return blocks, block_positions

# Function to calculate a hash for a block using magic square multiplication and block position
def calculate_magic_square_hash(block, magic_square, position):
    multiplied_block = block * magic_square
    block_flattened = multiplied_block.flatten()
    block_string = ''.join(map(str, block_flattened))
    position_string = ''.join(map(str, position))  # Convert position to string
    combined_string = block_string + position_string  # Combine block string and position string
    return sha256(combined_string.encode('utf-8')).hexdigest()

# Function to hash a pair of values
def hash_pair(left, right):
    return sha256((left + right).encode('utf-8')).hexdigest()

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

# Function to retrieve the stored root hash
def retrieve_root_hash(key_file="encryption_key.txt", storage_file="root_hash_storage.txt"):
    with open(key_file, "rb") as key_file:
        key = key_file.read()
    
    cipher_suite = Fernet(key)
    
    with open(storage_file, "rb") as file:
        encrypted_root_hash = file.read()
    
    root_hash = cipher_suite.decrypt(encrypted_root_hash).decode()
    return root_hash

# Function to build the Merkle tree and return the root hash
def build_merkle_tree(hashes):
    while len(hashes) > 1:
        new_level = []
        for i in range(0, len(hashes), 2):
            left = hashes[i]
            right = hashes[i+1] if i+1 < len(hashes) else hashes[i]
            new_level.append(hash_pair(left, right))
        hashes = new_level
    return hashes[0]

# Function to verify the image and check if it is tampered
def verify_image(image, magic_square, stored_root_hash):
    blocks, block_positions = divide_into_blocks(image, magic_square.shape[0])
    recalculated_hashes = [calculate_magic_square_hash(block, magic_square, position) for block, position in zip(blocks, block_positions)]
    
    recalculated_root_hash = build_merkle_tree(recalculated_hashes)

    # Compare recalculated root hash with the stored root hash
    is_tampered = recalculated_root_hash != stored_root_hash
    print(f"Is tampered: {is_tampered}")

    return is_tampered

# Main function to handle user inputs and verify the image
def main():
    parser = argparse.ArgumentParser(description="Verify an image and check if it is tampered.")
    parser.add_argument('image_path', type=str, help="Path to the received image")
    parser.add_argument('path_proofs', type=str, help="Path to the stored path proofs")

    args = parser.parse_args()

    # Load the image
    image = Image.open(args.image_path)
    image_array = np.array(image)

    # Check if image dimensions are multiples of block size
    if image_array.shape[0] % BLOCK_SIZE != 0 or image_array.shape[1] % BLOCK_SIZE != 0:
        print("Error: Image dimensions must be multiples of the block size.")
        return
    
    # Create the magic square
    magic_square = create_magic_square(BLOCK_SIZE)
    
    # Print the magic square
    print("Magic Square:")
    print(magic_square)
    
    # Retrieve the stored root hash
    stored_root_hash = retrieve_root_hash()
    
    # Verify the image
    is_tampered = verify_image(image_array, magic_square, stored_root_hash)

if __name__ == "__main__":
    main()
