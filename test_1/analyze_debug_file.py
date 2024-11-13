import re

def analyze_debug_file(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()
    
    total_blocks = 0
    matching_blocks = 0
    tampered_blocks = 0
    tampered_pixels = 0
    tampered_pixel_details = []

    block_pattern = re.compile(r'Block (\d+) hash matches\. Expected Hash: (.*), Actual Hash: (.*)')
    tampered_block_pattern = re.compile(r'Tampered block detected: Block (\d+) at position (\(\d+, \d+\))')
    tampered_pixel_pattern = re.compile(r'Pixel tampered at \((\d+), (\d+)\): Original (\d+), Tampered (\d+)')
    
    for line in lines:
        block_match = block_pattern.match(line)
        tampered_block_match = tampered_block_pattern.match(line)
        tampered_pixel_match = tampered_pixel_pattern.match(line)

        if block_match:
            total_blocks += 1
            matching_blocks += 1
        elif tampered_block_match:
            total_blocks += 1
            tampered_blocks += 1
        elif tampered_pixel_match:
            tampered_pixels += 1
            tampered_pixel_details.append(tampered_pixel_match.groups())
    
    print(f"Total blocks: {total_blocks}")
    print(f"Matching blocks: {matching_blocks}")
    print(f"Tampered blocks: {tampered_blocks}")
    print(f"Tampered pixels: {tampered_pixels}")
    print("\nTampered Pixel Details:")
    for detail in tampered_pixel_details:
        print(f"Pixel tampered at ({detail[0]}, {detail[1]}): Original {detail[2]}, Tampered {detail[3]}")

if __name__ == "__main__":
    analyze_debug_file('debug_output.txt')
