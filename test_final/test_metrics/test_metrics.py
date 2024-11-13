import json
from sklearn.metrics import confusion_matrix, accuracy_score, precision_score, recall_score, f1_score

def load_json(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def generate_block_pixels(block, block_size):
    by, bx = block  # (y, x) coordinates
    return [(bx + x, by + y) for x in range(block_size) for y in range(block_size)]

def calculate_metrics(ground_truth, detected_tampering, block_size):
    y_true = []
    y_pred = []

    for image_name, tampered_pixels in ground_truth.items():
        print(f"\nProcessing image: {image_name}")
        if image_name in detected_tampering:
            detected_blocks = detected_tampering[image_name]
            detected_pixels = set()
            for block in detected_blocks:
                block_pixels = generate_block_pixels(block, block_size)
                detected_pixels.update(tuple(pixel) for pixel in block_pixels)
            
            for pixel in tampered_pixels:
                pixel_tuple = tuple(pixel)
                is_detected = pixel_tuple in detected_pixels
                y_true.append(1)
                y_pred.append(1 if is_detected else 0)
                if not is_detected:
                    print(f"Failed to detect tampered pixel: {pixel} in image: {image_name}")
                else:
                    print(f"Successfully detected tampered pixel: {pixel} in image: {image_name}")

            for pixel in detected_pixels:
                if pixel not in map(tuple, tampered_pixels):
                    y_true.append(0)
                    y_pred.append(1)
        else:
            for pixel in tampered_pixels:
                y_true.append(1)
                y_pred.append(0)
                print(f"Image {image_name} not detected in detected log")

    if not y_true or not y_pred:
        print("No tampering detected or ground truth available to compare.")
        return
    
    cm = confusion_matrix(y_true, y_pred)
    if cm.size == 4:
        TN, FP, FN, TP = cm.ravel()
    else:
        TN, FP, FN, TP = 0, 0, 0, 0
        print("Confusion matrix does not have the correct size.")

    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, zero_division=1)
    recall = recall_score(y_true, y_pred, zero_division=1)
    f1 = f1_score(y_true, y_pred, zero_division=1)

    print("\nConfusion Matrix:")
    print(cm)
    print(f"Accuracy: {accuracy}")
    print(f"Precision: {precision}")
    print(f"Recall: {recall}")
    print(f"F1 Score: {f1}")

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Calculate tampering detection metrics.")
    parser.add_argument('ground_truth_file', type=str, help="Path to the ground truth tampering log")
    parser.add_argument('detected_file', type=str, help="Path to the detected tampering log")
    parser.add_argument('block_size', type=int, help="Block size used in the tampering detection")

    args = parser.parse_args()

    ground_truth = load_json(args.ground_truth_file)
    detected_tampering = load_json(args.detected_file)

    calculate_metrics(ground_truth, detected_tampering, args.block_size)

if __name__ == "__main__":
    main()
