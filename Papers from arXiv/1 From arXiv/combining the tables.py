#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 16 11:59:43 2024

@author: oliverguest
"""

import pandas as pd
import os

# List of CSV files to process
files_to_process = [
    # Add your file names here, e.g.:
    "safety_alignment_Aug_16.csv",
    "robust_Aug_16.csv",
    "other_Aug_16.csv"]

# Function to process a single CSV file
def process_csv(file_path):
    df = pd.read_csv(file_path)
    
    # Drop the "Search Term" column if it exists
    if "Search Term" in df.columns:
        df = df.drop(columns=["Search Term"])
    
    return df

# Main processing function
def main():
    all_data = []
    
    for file in files_to_process:
        if os.path.exists(file):
            df = process_csv(file)
            all_data.append(df)
        else:
            print(f"Warning: File {file} not found. Skipping.")
    
    if not all_data:
        print("No valid files were processed. Exiting.")
        return
    
    # Combine all dataframes
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # Remove duplicates based on arXiv ID
    combined_df.drop_duplicates(subset=["arXiv ID"], keep="first", inplace=True)
    
    # Save the processed dataframe to a CSV file
    combined_df.to_csv("combined.csv", index=False)
    print("Processing complete. Output saved to 'combined.csv'")

if __name__ == "__main__":
    main()