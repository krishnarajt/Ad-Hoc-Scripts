import os
import random
from PIL import Image
from pathlib import Path

def crop_to_square(image):
    width, height = image.size
    size = min(width, height)
    
    left = (width - size) // 2
    top = (height - size) // 2
    right = (width + size) // 2
    bottom = (height + size) // 2

    return image.crop((left, top, right, bottom))

def create_cover_image_for_folders(base_dir, images_folder, overwrite=True):
    images = [f for f in Path(images_folder).iterdir() if f.is_file() and f.suffix.lower() in {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}]

    if not images:
        print("No images found in the provided folder.")
        return

    for subfolder in Path(base_dir).iterdir():
        if subfolder.is_dir():
            cover_path = subfolder / 'cover.jpg'

            # Skip if overwrite is disabled and any image file already exists in the subfolder
            if not overwrite:
                existing_images = [f for f in subfolder.iterdir() if f.is_file() and f.suffix.lower() in {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}]
                if existing_images:
                    print(f"Skipping (image already exists): {subfolder}")
                    continue

            print(f"Creating cover for: {subfolder}")

            if not images:
                print("Ran out of images to assign.")
                break

            image_path = random.choice(images)
            images.remove(image_path)

            img = Image.open(image_path)
            img_cropped = crop_to_square(img)
            img_cropped.save(cover_path)
            print(f"Cover image saved at: {cover_path}")

if __name__ == "__main__":
    base_directory = input("Enter the base folder path: ").strip()
    images_folder = input("Enter the folder path containing images: ").strip()
    overwrite_input = input("Overwrite existing cover images? (yes/no): ").strip().lower()

    overwrite = overwrite_input != 'no'

    if os.path.isdir(base_directory) and os.path.isdir(images_folder):
        create_cover_image_for_folders(base_directory, images_folder, overwrite)
    else:
        print("The provided paths are not valid.")