import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import pandas as pd
import json
from tqdm.auto import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

#import dataframe from CSV. The CSV comes from exporting the "Export" sheet in the Google Sheet.
df = pd.read_csv('ODA_papers.csv')

#Replacing company websites with arXiv links if the webpage links to one

def find_arxiv_link_in_page(url):
    """Fetch a webpage and look for a link to arXiv with specific link text or aria-label."""
    try:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            # Search for all 'a' tags to scrutinize individually
            all_links = soup.find_all('a')
            for link in all_links:
                # Check if 'Read paper' is in the link text or 'aria-label' and the href contains 'arxiv.org'
                if 'arxiv.org' in link.get('href', '') and ('read paper' in link.text.lower() or link.get('aria-label', '').lower() == 'read paper'):
                    return link['href']
    except Exception as e:
        print(f"Error fetching or parsing {url}: {e}")
    return None

def process_urls(urls):
    """Process a list of URLs, replacing specific links with their arXiv counterparts."""
    updated_urls = []
    for i, url in enumerate(urls, 1):  # Start counting from 1
        if 'arxiv.org' not in url:
            arxiv_url = find_arxiv_link_in_page(url)
            updated_urls.append(arxiv_url if arxiv_url else url)
        else:
            updated_urls.append(url)
        print(f"{i}/{len(urls)} done")
    return updated_urls

df['URL_processed'] = process_urls(df['URL'].tolist())

# Save DataFrame
df.to_csv('ODA_papers_processed.csv', index=False)


#function to get the title and abstract from an arXiv URL
#I guess would be good to add the funtionality of switching back to the original URL once the processing is done

def extract_arXiv(url):
    # Extract the arXiv ID from the URL
    arxiv_id = url.split('/')[-1]
    
    # Define the arXiv API endpoint with the arXiv ID
    api_url = f'http://export.arxiv.org/api/query?id_list={arxiv_id}'
    
    # Make the GET request to the arXiv API
    response = requests.get(api_url)
    
    # Check if the request was successful
    if response.status_code == 200:
        # Parse the XML response
        root = ET.fromstring(response.content)
        
        # Namespace dictionary to handle the arXiv namespace
        ns = {'arxiv': 'http://www.w3.org/2005/Atom'}
        
        # Find the entry tag in the response
        entry = root.find('arxiv:entry', ns)
        
        # Extract the title and abstract from the entry, remove leading and trailing whitespace
        abstract = entry.find('arxiv:summary', ns).text.strip()
        
        return abstract
    else:
        return None
    
    #function to get the title and abstract from a DeepMind URL

def extract_GDM(url):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Attempt to find the <h2> tag containing the text "Abstract"
        abstract_heading = soup.find(lambda tag: tag.name == 'h2' and 'Abstract' in tag.text)
        
        # Check if the abstract heading was found before proceeding
        if abstract_heading:
            # Find the next <p> tag which is assumed to contain the abstract
            abstract_paragraph = abstract_heading.find_next('p')
            abstract = abstract_paragraph.text.strip() if abstract_paragraph else 'Abstract not found'
        else:
            abstract = 'Abstract not found'
        
        return abstract
    else:
        return None
    
    #function to get the title and abstract from an OpenReview URL

def extract_openreview(url):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
        if script_tag:
            data = json.loads(script_tag.string)
            abstract = data['props']['pageProps']['forumNote']['content'].get('abstract', 'Abstract not found')
        else:
            abstract = 'Abstract not found'
        
        return abstract
    else:
        return None
    
    #function to get the title and abstract from an Anthropic URL

def extract_Anthropic(url):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        # Locate the abstract based on the <h4> tag using the 'string' argument instead of 'text'
        abstract_marker = soup.find('h4', string='Abstract')
        abstract = abstract_marker.find_next_sibling('p').text.strip() if abstract_marker else 'Abstract not found'

        return abstract
        
    else:
        return None
    
    #Note that the OAI pages are pretty inconsistent so this won't work for all of them.

def extract_OAI(url):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the abstract. It's in the <div> following the <h2> tag containing "Abstract"
        try:
            abstract_section = soup.find('h2', string='Abstract').find_next_sibling('div')
            abstract = ' '.join(abstract_section.stripped_strings) if abstract_section else 'Abstract not found'
        except:
            abstract = 'Abstract not found'
        else:
            abstract_section = soup.find('h2', string='Abstract').find_next_sibling('div')
            abstract = ' '.join(abstract_section.stripped_strings) if abstract_section else 'Abstract not found'
        
        return abstract
    else:
        return None
    
# Function to extract the abstract from a given URL based on the domain
def extract_abstract(url):
    try:
        # Check the domain and call the appropriate extraction function
        domain = urlparse(url).netloc
        if 'arxiv.org' in domain:
            return extract_arXiv(url)
        elif 'deepmind.google' in domain:
            return extract_GDM(url)
        elif 'anthropic.com' in domain:
            return extract_Anthropic(url)
        elif 'openai.com' in domain:
            return extract_OAI(url)
        elif 'openreview.net' in domain:
            return extract_openreview(url)
        else:
            return None  # Domain not recognized
    except Exception as e:
        return None  # In case of an error, return None

tqdm.pandas(desc="Extracting abstracts")

# Use progress_apply instead of apply to see the progress bar
df['Abstract'] = df['URL_processed'].progress_apply(extract_abstract)

# handle papers whose abstracts were added manually
manualDF  = pd.read_csv('Manually adding abstracts.csv',header=None,names=["URL","Abstract"])

# Merge the two DataFrames on the 'URL' column with a left join to keep all rows from `df`
combined_df = pd.merge(df, manualDF, on='URL', how='left', suffixes=('', '_manual'))

# Where the 'Abstract_manual' is not null (meaning there is a manually added abstract), 
# replace the 'Abstract' with the 'Abstract_manual' value
combined_df['Abstract'] = combined_df.apply(
    lambda row: row['Abstract_manual'] if pd.notnull(row['Abstract_manual']) else row['Abstract'],
    axis=1
)

# Drop the 'Abstract_manual' column as it's no longer needed
combined_df.drop(columns='Abstract_manual', inplace=True)

# Write the updated DataFrame back to a CSV
combined_df.to_csv('ODA_papers_with_abstracts.csv', index=False)