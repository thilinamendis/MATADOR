import numpy as np
from PIL import Image
import os
from script_A import divide_into_blocks, create_magic_square, add_padding, generate_possible_magic_numbers  # Import necessary functions

# Function to prepare training data with variations
def prepare_training_data(original_image_path, tampered_image_paths, block_sizes, start_num_range):
    training_data = []

    for block_size in block_sizes:
        start_nums = list(range(start_num_range[0], start_num_range[1]))
        possible_magic_numbers = generate_possible_magic_numbers(block_size, start_nums)
        for magic_number, start_num in possible_magic_numbers:
            # Ensure the generated magic square has the correct magic number
            magic_square = create_magic_square(block_size, start_num)
            if np.sum(magic_square[0]) != magic_number:
                continue

            # Process original image
            original_image = Image.open(original_image_path).convert('L')
            original_image = np.array(original_image)
            if original_image.shape[0] % block_size != 0 or original_image.shape[1] % block_size != 0:
                original_image = add_padding(original_image, block_size)

            blocks, block_positions = divide_into_blocks(original_image, block_size)
            for block, position in zip(blocks, block_positions):
                transformed_block = block * magic_square
                label = 0  # Label for original block
                training_data.append((transformed_block.flatten(), label))

            # Process tampered images
            for tampered_image_path in tampered_image_paths:
                tampered_image = Image.open(tampered_image_path).convert('L')
                tampered_image = np.array(tampered_image)
                if tampered_image.shape[0] % block_size != 0 or tampered_image.shape[1] % block_size != 0:
                    tampered_image = add_padding(tampered_image, block_size)

                blocks, block_positions = divide_into_blocks(tampered_image, block_size)
                for block, position in zip(blocks, block_positions):
                    transformed_block = block * magic_square
                    label = 1  # Label for tampered block
                    training_data.append((transformed_block.flatten(), label))

    # Save training data
    np.save("training_data.npy", training_data)
    print("Training data prepared and saved to training_data.npy")

# Main function to handle user inputs
if __name__ == "__main__":
    original_image_path = "Person_A/images/original_image.jpeg"
    tampered_image_paths = [f"Hacker/images/tampered_image_{i}.jpeg" for i in range(10)]
    block_sizes = [3, 4, 5, 6, 7, 8]  # Including odd, even, singly-even, and doubly-even block sizes
    start_num_range = (2, 12)  # Example range for start numbers

    prepare_training_data(original_image_path, tampered_image_paths, block_sizes, start_num_range)
    print("Note: If the range for starting numbers changes in Script A, update start_num_range in this script and regenerate the training data.")
