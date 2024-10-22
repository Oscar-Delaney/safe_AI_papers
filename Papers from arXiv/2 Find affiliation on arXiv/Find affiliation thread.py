#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 16 12:13:10 2024

@author: oliverguest
"""

import pandas as pd
import requests
import io
import fitz  # PyMuPDF
import re
from anthropic import Anthropic
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial

api_key = input("Please enter your Anthropic API key: ")
client = Anthropic(api_key=api_key)

# Define the maximum number of threads
MAX_WORKERS = 6  # Adjust based on your system and API rate limits

def download_pdf(url, session, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            response = session.get(url, timeout=10)
            response.raise_for_status()  # Raise an exception for HTTP errors
            return io.BytesIO(response.content)
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}. Retrying...")
            time.sleep(1)  # Wait for 1 second before retrying
    print(f"Failed to download PDF after {max_attempts} attempts for URL: {url}")
    return None

def extract_first_page_text(pdf_content):
    try:
        with fitz.open(stream=pdf_content, filetype="pdf") as doc:
            if len(doc) > 0:
                page = doc.load_page(0)
                return page.get_text()
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
    return ""

def process_text(text):
    return re.sub(r'\s+', '', text.lower())

def check_companies(text):
    companies = ["openai", "anthropic", "google", "deepmind"]
    return any(company in text for company in companies)

def get_affiliation_1(text):
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=256,
            temperature=0,
            system="You will see text taken from the first page of a journal article. Your answer will be the affiliation or affiliations of the first author, such as their university or company. Write a few tokens before saying the institution so that you have more time to think. If the answer is unclear, say that.",
            messages=[
                {"role": "user", "content": text}
            ]
        )
        return response.content[0].text.strip()
    except Exception as e:
        return f"[LLM extraction failed: {str(e)}]"

def get_affiliation_2(text):
    try:
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=256,
            temperature=0,
            system="What institution(s) does the first author belong to? Just write the institution(s) or '[Unclear]'. If there are multiple institutions, use \" · \" to separate them.",
            messages=[
                {"role": "user", "content": text}
            ]
        )
        return response.content[0].text.strip()
    except Exception as e:
        return f"[LLM extraction failed: {str(e)}]"

def process_paper(row, session):
    print(f"Processing paper: {row['Title']}")
    # Step 1: Get the text from the first page of the PDF
    pdf_content = download_pdf(row['PDF_Link'], session)
    if pdf_content is None:
        return "[PDF processing failed]", "[PDF processing failed]"

    first_page_text = extract_first_page_text(pdf_content)
    if not first_page_text:
        return "[PDF processing failed]", "[PDF processing failed]"

    # Step 2: String filtering
    processed_text = process_text(first_page_text)
    if not check_companies(processed_text):
        return "[ODA not mentioned on first page; discarded]", "[Not ODA]"

    # Step 3: Using LLMs to identify institutions
    affiliation_step_1 = get_affiliation_1(first_page_text)
    if affiliation_step_1.startswith("[LLM extraction failed"):
        return affiliation_step_1, affiliation_step_1

    affiliation_step_2 = get_affiliation_2(affiliation_step_1)
    if affiliation_step_2.startswith("[LLM extraction failed"):
        return affiliation_step_1, affiliation_step_2

    return affiliation_step_1, affiliation_step_2

def save_progress(df, file, count):
    df.to_csv(file, index=False)
    print(f"Processed {count} papers and saved to file.")

def main():
    # Define the file name here
    file = "data_Sep_23.csv"

    # Load the CSV file
    df = pd.read_csv(file)

    # Ensure 'Affiliation_step_1' and 'Institution' columns exist
    if 'Affiliation_step_1' not in df.columns:
        df['Affiliation_step_1'] = ''
    if 'Institution' not in df.columns:
        df['Institution'] = ''

    # Initialize a requests session
    session = requests.Session()

    # Set how often to save the DataFrame
    save_every = 50
    counter = 0

    # Prepare list of rows to process
    rows_to_process = df[df['Institution'].isna() | (df['Institution'] == '')].to_dict('records')

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Properly utilize partial to fix the unused 'process_func'
        process_func = partial(process_paper, session=session)
        
        # Submit all tasks
        future_to_index = {
            executor.submit(process_func, row): index 
            for index, row in df.iterrows() 
            if pd.isna(row['Institution']) or row['Institution'] == ''
        }

        for future in as_completed(future_to_index):
            row_index = future_to_index[future]  # Corrected mapping
            try:
                affiliation_1, affiliation_2 = future.result()
                df.at[row_index, 'Affiliation_step_1'] = affiliation_1
                df.at[row_index, 'Institution'] = affiliation_2
                counter += 1
                if counter % save_every == 0:
                    save_progress(df, file, counter)
            except Exception as e:
                print(f"Error processing paper at index {row_index}: {e}")

    # Save any remaining data
    df.to_csv(file, index=False)
    print(f"All papers processed and saved to file.")

if __name__ == "__main__":
    main()
