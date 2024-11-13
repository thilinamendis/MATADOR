import numpy as np
from hashlib import sha256
from cryptography.fernet import Fernet
from PIL import Image, ImageDraw
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

# Function to verify the image and identify tampered blocks using path proofs
def verify_image(image, magic_square, stored_root_hash, path_proofs):
    blocks, block_positions = divide_into_blocks(image, magic_square.shape[0])
    recalculated_hashes = [calculate_magic_square_hash(block, magic_square, position) for block, position in zip(blocks, block_positions)]
    
    tampered_blocks = []
    for idx, (block, position) in enumerate(zip(blocks, block_positions)):
        block_hash = recalculated_hashes[idx]
        proof = path_proofs[idx]
        computed_hash = block_hash
        for sibling_hash in proof:
            if int(computed_hash, 16) < int(sibling_hash, 16):
                computed_hash = hash_pair(computed_hash, sibling_hash)
            else:
                computed_hash = hash_pair(sibling_hash, computed_hash)

        # If the computed hash does not match the stored root hash, the block is tampered
            if computed_hash != stored_root_hash:
                tampered_blocks.append(position)
                print(f"Tampered block detected at {position}: Recalculated Hash = {block_hash}")

    print(f"Total tampered blocks: {len(tampered_blocks)}")
    print(f"Tampered blocks: {tampered_blocks}")

    return tampered_blocks

# Main function to handle user inputs and verify the image
def main():
    parser = argparse.ArgumentParser(description="Verify an image and generate block hashes.")
    parser.add_argument('image_path', type=str, help="Path to the received image")
    parser.add_argument('path_proofs', type=str, help="Path to the stored path proofs")

    args = parser.parse_args()

    # Load the image
    image = Image.open(args.image_path).convert('L')
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
    
    # Load the path proofs
    with open(args.path_proofs, "r") as file:
        path_proofs = json.load(file)
    
    # Verify the image
    tampered_blocks = verify_image(image_array, magic_square, stored_root_hash, path_proofs)

    # Highlight tampered pixels in the image
    if tampered_blocks:
        tampered_image = Image.open(args.image_path).convert('RGB')
        draw = ImageDraw.Draw(tampered_image)
        for position in tampered_blocks:
            i, j = position
            for bi in range(BLOCK_SIZE):
                for bj in range(BLOCK_SIZE):
                    draw.rectangle([j+bj, i+bi, j+bj+1, i+bi+1], outline="red")
        
        tampered_image.save("tampered_analysis.jpeg")
        print("Tampered areas highlighted and saved as tampered_analysis.jpeg")

if __name__ == "__main__":
    main()
