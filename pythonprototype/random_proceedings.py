import os
import random
import shutil

def extract_random_files(source_folder, output_folder, sample=6, seed=None):
    if seed is not None:
        random.seed(seed)

    os.makedirs(output_folder, exist_ok=True)

    files = [f for f in os.listdir(source_folder) if os.path.isfile(os.path.join(source_folder, f))]

    selected_files = random.sample(files, sample)

    for file in selected_files:
        src_path = os.path.join(source_folder, file)
        out_path = os.path.join(output_folder, file)
        shutil.copy2(src_path, out_path)

if __name__ == "__main__":
    folder_path = "lakproceedings"
    output_folder_path = "randomproceedings"

    extract_random_files(folder_path, output_folder_path, sample=12, seed=42)