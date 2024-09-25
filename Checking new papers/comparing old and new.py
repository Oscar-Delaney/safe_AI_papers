import csv
import os
from collections import defaultdict

def read_csv(filename):
    with open(filename, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        data = {}
        for row in reader:
            if 'Date' in row:
                del row['Date']  # Remove the 'Date' column if present
            data[row['URL']] = row
        return data

def write_csv(filename, fieldnames, rows):
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def compare_csv_files(company):
    old_file = f'old_{company}.csv'
    new_file = f'new_{company}.csv'
    output_file = f'comparison_{company}.csv'

    old_data = read_csv(old_file)
    new_data = read_csv(new_file)

    all_urls = set(old_data.keys()) | set(new_data.keys())

    output_rows = []
    for url in all_urls:
        if url in old_data and url in new_data:
            row = new_data[url]
            row['New paper?'] = 'Both'
        elif url in new_data:
            row = new_data[url]
            row['New paper?'] = 'New'
        else:
            row = old_data[url]
            row['New paper?'] = 'Old'
        output_rows.append(row)

    fieldnames = ['Company', 'Title', 'URL', 'Safety_category', 'Abstract', 'New paper?']
    write_csv(output_file, fieldnames, output_rows)

def main():
    companies = ['Anthropic', 'GDM', 'OpenAI']
    for company in companies:
        compare_csv_files(company)
    print("Comparison files have been generated.")

if __name__ == "__main__":
    main()