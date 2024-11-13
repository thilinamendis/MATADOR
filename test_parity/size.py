import os
from PIL import Image

# Define the folder path
folder_path = "Data/"

# Define the required dimensions
required_width = 630
required_height = 630

# Initialize a counter for renaming
image_counter = 1

# Loop through all the files in the folder
for filename in os.listdir(folder_path):
    file_path = os.path.join(folder_path, filename)
    
    # Check if the file is an image
    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
        try:
            # Open the image
            with Image.open(file_path) as img:
                # Check the size of the image
                if img.size == (required_width, required_height):
                    # Create a new name for the image
                    new_name = f"test_image_{image_counter}.png"
                    new_file_path = os.path.join(folder_path, new_name)
                    
                    # Rename the image
                    os.rename(file_path, new_file_path)
                    print(f"Renamed {filename} to {new_name}.")
                    
                    # Increment the counter
                    image_counter += 1
                else:
                    print(f"Deleting {filename} as it is not 630x630 pixels.")
                    os.remove(file_path)  # Delete the image if it doesn't match
        except Exception as e:
            print(f"Could not process {filename}. Error: {e}")
    else:
        print(f"{filename} is not an image, skipping.")
