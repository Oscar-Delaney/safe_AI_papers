import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import pandas as pd

#import dataframe from CSV. The CSV comes from exporting the "Export" sheet in the Google Sheet.
df = pd.read_csv('ODApapers.csv')

#clean up df
df.rename(columns={'Paper (title + link)': 'Title'}, inplace=True)
df['Title'] = df['Title'].str.replace('\n', ' ', regex=False)

urls = df['URL'].tolist()

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
    for url in urls:
        if 'arxiv.org' not in url:
            arxiv_url = find_arxiv_link_in_page(url)
            if arxiv_url:
                updated_urls.append(arxiv_url)
            else:
                updated_urls.append(url)
        else:
            updated_urls.append(url)
    return updated_urls

urls = process_urls(urls)

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
        title = entry.find('arxiv:title', ns).text.strip()
        abstract = entry.find('arxiv:summary', ns).text.strip()
        
        return title, abstract
    else:
        return "Failed to retrieve."
    
    #function to get the title and abstract from a DeepMind URL

def extract_GDM(url):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract the title from the page
        title = soup.title.text.strip() if soup.title else 'Title not found'
        
        # Attempt to find the <h2> tag containing the text "Abstract"
        abstract_heading = soup.find(lambda tag: tag.name == 'h2' and 'Abstract' in tag.text)
        
        # Check if the abstract heading was found before proceeding
        if abstract_heading:
            # Find the next <p> tag which is assumed to contain the abstract
            abstract_paragraph = abstract_heading.find_next('p')
            abstract = abstract_paragraph.text.strip() if abstract_paragraph else 'Abstract not found'
        else:
            abstract = 'Abstract not found'
        
        return title, abstract
    else:
        return "Failed to retrieve."
    
    #function to get the title and abstract from an Anthropic URL

def extract_Anthropic(url):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the title
        title = soup.find('h1').text.strip() if soup.find('h1') else 'Title not found'

        # Locate the abstract based on the <h4> tag using the 'string' argument instead of 'text'
        abstract_marker = soup.find('h4', string='Abstract')
        abstract = abstract_marker.find_next_sibling('p').text.strip() if abstract_marker else 'Abstract not found'

        return title, abstract
        
    else:
        return "Failed to retrieve."
    
    #Note that the OAI pages are pretty inconsistent so this won't work for all of them.

def extract_OAI(url):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Locate the correct <h1> element for the title. Assuming it's the first <h1> inside a specific div
        title_container = soup.find('div', class_='ui-hero')
        title = title_container.find('h1').text.strip() if title_container else 'Title not found'
        
        # Find the abstract. It's in the <div> following the <h2> tag containing "Abstract"
        try:
            abstract_section = soup.find('h2', string='Abstract').find_next_sibling('div')
            abstract = ' '.join(abstract_section.stripped_strings) if abstract_section else 'Abstract not found'
        except:
            abstract = 'Abstract not found'
        else:
            abstract_section = soup.find('h2', string='Abstract').find_next_sibling('div')
            abstract = ' '.join(abstract_section.stripped_strings) if abstract_section else 'Abstract not found'
        
        return title, abstract
    else:
        return "Failed to retrieve webpage"
    
#defining lists that are used for the dataframes
title_abstract = []
errors = []

#function to turn a URL into just the domain, e.g. google.com
def url_to_domain(url):
    # Parse the URL to extract the domain
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    return(domain)

#function to add the processed the scraped info to the working or error df
def process_scraped_info(output):
    if output == "Failed to retrieve.":
        errors.append((url,output))
    else:
        title_abstract.append((*output,url))
        
#Processing the scraped info for each of the domains
for url in urls:
    if 'arxiv.org' in url_to_domain(url):
        output = extract_arXiv(url)
        process_scraped_info(output)
    elif 'deepmind.google' in url_to_domain(url):
        output = extract_GDM(url)
        process_scraped_info(output)
    elif 'anthropic.com' in url_to_domain(url):
        output = extract_Anthropic(url)
        process_scraped_info(output)
    elif 'openai.com' in url_to_domain(url):
        output = extract_OAI(url)
        process_scraped_info(output)
    else:
        errors.append((url,"You haven't set up scraping for this website."))



mainDF = pd.DataFrame(title_abstract, columns=['Title', 'Abstract','URL'])


# Assuming df is your DataFrame and errors is the list to append errors to

# To store indices of rows to be removed
rows_to_remove = []

for index, row in mainDF.iterrows():
    if "not found" in row['Title'] and "not found" in row['Abstract']:
        errors.append((row['URL'], "Abstract and title both not found"))
        rows_to_remove.append(index)
    elif row['Title'] == "Title not found":
        errors.append((row['URL'], "Title not found"))
        rows_to_remove.append(index)
    elif row['Abstract'] == "Abstract not found":
        errors.append((row['URL'], "Abstract not found"))
        rows_to_remove.append(index)

# Remove the rows from the DataFrame
mainDF = mainDF.drop(rows_to_remove)

#handle papers whose abstracts were added manually

manualDF  = pd.read_csv('Manually adding abstracts.csv',header=None,names=["URL","Abstract"])
manualDF = manualDF.loc[manualDF['Abstract'] != "-"]


# Function to get title from URL
def get_title(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        title = soup.find('title').text
    except Exception as e:
        print(f"Error fetching title for {url}: {e}")
        title = "N/A"
    return title

# Apply the function to the 'URL' column and create a new 'Title' column
manualDF['Title'] = manualDF['URL'].apply(get_title)

# Reorder the DataFrame columns
manualDF = manualDF[['Title', 'Abstract', 'URL']]

#concatenate the successful data frames
mainDF = pd.concat([mainDF, manualDF], ignore_index=True)

#write to CSV
mainDF.to_csv('Papers with abstracts.csv', columns=['Title', 'Abstract'], index=False)