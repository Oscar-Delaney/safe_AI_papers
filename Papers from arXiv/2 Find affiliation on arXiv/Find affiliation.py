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

# Add Anthropic API key

def download_pdf(url):
    try:
        response = requests.get(url)
        return io.BytesIO(response.content)
    except:
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
    companies = ["microsoft", "baidu", "meta", "openai", "nvidia", "huawei", "yandex", "anthropic", "google", "deepmind"]
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
        return "[No AI company mentioned on first page; discarded]", "[Not an AI company]"
    
    # Step 3: Using LLMs to identify institutions
    affiliation_step_1 = get_affiliation_1(first_page_text)
    if affiliation_step_1.startswith("[LLM extraction failed"):
        return affiliation_step_1, affiliation_step_1
    
    affiliation_step_2 = get_affiliation_2(affiliation_step_1)
    if affiliation_step_2.startswith("[LLM extraction failed"):
        return affiliation_step_1, affiliation_step_2
    
    return affiliation_step_1, affiliation_step_2

def main():
    # Load the CSV file
    df = pd.read_csv('combined.csv')

    
    # For testing purposes, select just the first 10 rows
    #df = df.head(10)
    
    # Ensure 'Affiliation_step_1' and 'Institution' columns exist
    if 'Affiliation_step_1' not in df.columns:
        df['Affiliation_step_1'] = ''
    if 'Institution' not in df.columns:
        df['Institution'] = ''
    
    # Process each unprocessed paper
    for index, row in df.iterrows():
        # Check if the paper needs processing
        if (pd.isna(row['Institution']) or 
            row['Institution'] == '' or 
            row['Institution'].startswith('[')) and row['Institution'] != "[Not an AI company]":
            affiliation_1, affiliation_2 = process_paper(row)
            df.at[index, 'Affiliation_step_1'] = affiliation_1
            df.at[index, 'Institution'] = affiliation_2
            
            # Save the df after every row
            df.to_csv('combined.csv', index=False)
            print(f"Processed and saved paper {index + 1}")  # Added for debugging
        else:
            print(f"Skipping already processed or non-AI company paper {index + 1}")  # Updated debugging message
        
        #time.sleep(0.5)  # Added 0.5 second delay between each row
    
    # Change column name before final output
    #df = df.rename(columns={'Affiliation_step_1': 'Initial pass on determining institution'})
    df.to_csv('combined.csv', index=False)

if __name__ == "__main__":
    main()