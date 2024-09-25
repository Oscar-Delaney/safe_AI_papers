import urllib.parse
import urllib.request
import feedparser
import pandas as pd
import time
from datetime import date

def search_arxiv(query, start=0, max_results=100):
    base_url = 'http://export.arxiv.org/api/query?'
    search_query = urllib.parse.quote(query)
    url = f"{base_url}search_query={search_query}&start={start}&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
    response = urllib.request.urlopen(url)
    feed = feedparser.parse(response.read())
    total_results = int(feed.feed.opensearch_totalresults)
    return feed.entries, total_results

def fetch_batch(query, start, batch_size):
    max_attempts = 10
    delay = 3
    for attempt in range(max_attempts):
        try:
            results, _ = search_arxiv(query, start=start, max_results=batch_size)
            if results:
                return results
            print(f"Attempt {attempt + 1}: Empty batch. Retrying...")
            time.sleep(delay)
            delay *= 2  # Increase delay for next attempt
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {str(e)}. Retrying...")
            time.sleep(delay)
            delay *= 2  # Increase delay for next attempt
    print(f"Failed to fetch batch after {max_attempts} attempts.")
    return []

def main():
    search_terms = [
        #The arXiv API doesn't seem to return results when the term has a hyphen
        #but the non-hyphenated version of the term does return papers that have a hyphen in them.
        "Power seeking",
        "Seek power",
        "Multiagent",
        "Model organism*",
        "Safe* by design",
        "Brain emulation",
        "Interpretab*",
        "Honest",
        "Automat* alignment",
        "Automat* safety",
        "Human feedback",
        "Enhanc* feedback"
    ]

    base_query = ' AND (cat:cs.AI OR cat:cs.LG) AND submittedDate:[2022-01-01 TO 2024-06-30]'
    queries = [f'(ti:"{term}"){base_query}' for term in search_terms]
    
    all_data = {}
    duplicates = []

    for query_num, query in enumerate(queries, 1):
        print(f"\nProcessing Query {query_num} for term: {search_terms[query_num-1]}")
        print(query)
        _, total_results = search_arxiv(query, max_results=1)
        print(f"Total number of papers found: {total_results}")

        batch_size = 100
        for start in range(0, total_results, batch_size):
            print(f"Fetching results {start+1} to {min(start+batch_size, total_results)}...")
            results = fetch_batch(query, start, batch_size)
            
            if results:
                print(f"First paper in batch: {results[0].title}")
                print(f"Last paper in batch: {results[-1].title}")
            
            for paper in results:
                if '2021-01-01' <= paper.published[:10] <= '2024-06-30':
                    arxiv_id = paper.id.split('/abs/')[-1]
                    if arxiv_id not in all_data:
                        all_data[arxiv_id] = {
                            'Title': paper.title,
                            'Authors': ', '.join(author.name for author in paper.authors),
                            'Abstract': paper.summary,
                            'arXiv ID': arxiv_id,
                            'PDF_Link': f"https://arxiv.org/pdf/{arxiv_id}",
                            'Search Term': search_terms[query_num-1]
                        }
                    else:
                        duplicates.append(paper.title)
            time.sleep(3)  # Be nice to the API

    df = pd.DataFrame(list(all_data.values()))
    print(f"\nRetrieved {len(df)} unique papers:")
    print(df)

    print("\nDuplicate papers removed:")
    for dup in duplicates:
        print(dup)

    # Save to CSV
    today = date.today().strftime("%b_%d")
    csv_filename = f'other_{today}.csv'
    df.to_csv(csv_filename, index=False)
    print(f"\nData saved to {csv_filename}")

if __name__ == "__main__":
    main()