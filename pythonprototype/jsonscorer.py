import json
import os
import csv

def evaluate_json(data):
    score = 0
    for category in data["evaluation"]:
        category_name = category["category"]
        criteria = category["results"]
        if category_name == "Type of Analysis":
            if any(result["status"] != "Not Met" for result in criteria):
                score += 1
        else:
            if all(result["status"] != "Not Met" for result in criteria):
                score += 1
    return score

def evaluate_all_json(directory):
    results = []
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            filepath = os.path.join(directory, filename)
            with open(filepath, "r", encoding="utf-8") as file:
                data =json.load(file)

            file_id = data["id"]

            score = evaluate_json(data)
            if score == 5:
                reproducible = "yes"
            else:
                reproducible = "no"
            results.append([file_id, score, reproducible])
    return results

def save_as_csv(output_csv):
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['id', 'score', 'reproducible'])
        writer.writerows(results)
    print(f"Results saved to: {output_csv}")


if __name__ == "__main__":
    folder_path = "generatedjson"
    output_csv_path = "evaluation_results.csv"

    results = evaluate_all_json(folder_path)
    save_as_csv(output_csv_path)
