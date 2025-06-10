import json
import os
import csv

from unicodedata import category


def evaluate_json(data):
    score = 0
    category_statuses = {}
    for category in data["evaluation"]:
        category_name = category["category"]
        criteria = category["results"]
        if category_name == "Type of Analysis":
            if any(result["status"] != "Not Met" for result in criteria):
                score += 1
                category_statuses[category_name] = "Met"
            else:
                category_statuses[category_name] = "Not Met"

        elif category_name == "Preregistration":
            if all(result["status"] != "Not Met" for result in criteria):
                category_statuses[category_name] = "Met"
            else:
                category_statuses[category_name] = "Not Met"

        else:
            if all(result["status"] != "Not Met" for result in criteria):
                score += 1
                category_statuses[category_name] = "Met"
            else:
                category_statuses[category_name] = "Not Met"

    return score, category_statuses

def evaluate_all_json(directory):
    results = []
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            filepath = os.path.join(directory, filename)
            with open(filepath, "r", encoding="utf-8") as file:
                data =json.load(file)

            file_id = data["id"]
            score, category_statuses = evaluate_json(data)

            if score == 5:
                reproducible = "yes"
            else:
                reproducible = "no"

            row = [file_id, score,reproducible]
            for category in category_statuses:
                row.append(category_statuses[category])

            results.append((row, category_statuses))
    return results

def save_as_csv(output_csv, results):
    _, category_order = results[0]
    header = ["id","score","reproducible"] + list(category_order)

    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(header)
        for row, _ in results:
            writer.writerow(row)
    print(f"Results saved to: {output_csv}")


if __name__ == "__main__":
    folder_path = "generatedjson"
    output_csv_path = "evaluation_results.csv"

    results = evaluate_all_json(folder_path)
    save_as_csv(output_csv_path, results)
