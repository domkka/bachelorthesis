import os
import random
import shutil

def extract_random_files(source_folder, output_folder, sample=2, seed=None):
    if seed is not None:
        random.seed(seed)

    os.makedirs(output_folder, exist_ok=True)

    files = [f for f in os.listdir(source_folder) if os.path.isfile(os.path.join(source_folder, f))]

    already_selected = set(
        f for f in os.listdir(output_folder) if os.path.isfile(os.path.join(output_folder, f))
    )

    availabel_files = [f for f in files if f not in already_selected]

    selected_files = random.sample(availabel_files, sample)

    for file in selected_files:
        print(file)
        src_path = os.path.join(source_folder, file)
        out_path = os.path.join(output_folder, file)
        shutil.copy2(src_path, out_path)

if __name__ == "__main__":
    folder_path = "lakproceedings"
    output_folder_path = "randomproceedings"

    extract_random_files(folder_path, output_folder_path, sample=1, seed=42)