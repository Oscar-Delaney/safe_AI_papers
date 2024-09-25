#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 16 12:13:10 2024

@author: oliverguest
"""

import pandas as pd
import requests
import io
from PyPDF2 import PdfReader
import re
from anthropic import Anthropic
import time  # Added for delay

api_key = input("Please enter your Anthropic API key: ")
client = Anthropic(api_key=api_key)


def download_pdf(url, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            response = requests.get(url)
            return io.BytesIO(response.content)
        except:
            print(f"Attempt {attempt + 1} failed. Retrying...")
            time.sleep(1)  # Wait for 1 second before retrying
    print(f"Failed to download PDF after {max_attempts} attempts")
    return None

def extract_first_page_text(pdf_content):
    try:
        pdf = PdfReader(pdf_content)
        if len(pdf.pages) > 0:
            return pdf.pages[0].extract_text()
    except:
        pass
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
        return response.content[0].text
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
        return response.content[0].text
    except Exception as e:
        return f"[LLM extraction failed: {str(e)}]"

def process_paper(row):
    print(f"Processing paper: {row['Title']}")  # Added for debugging
    # Step 1: Get the text from the first page of the PDF
    pdf_content = download_pdf(row['PDF_Link'])
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
    
    # Process each unprocessed paper
    for index, row in df.iterrows():
        # Check if the paper needs processing (only if 'Institution' is empty)
        if pd.isna(row['Institution']) or row['Institution'] == '':
            print(f"Processing paper {index + 1}: {row['Title']}")
            affiliation_1, affiliation_2 = process_paper(row)
            df.at[index, 'Affiliation_step_1'] = affiliation_1
            df.at[index, 'Institution'] = affiliation_2
            
            # Save the df after every row
            df.to_csv(file, index=False)
            print(f"Processed and saved paper {index + 1}")
        else:
            print(f"Skipping already processed paper {index + 1}: {row['Title']} (Institution: {row['Institution']})")
        


if __name__ == "__main__":
    main()