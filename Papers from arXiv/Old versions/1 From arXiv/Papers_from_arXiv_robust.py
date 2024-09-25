import urllib.parse
import urllib.request
import feedparser
import pandas as pd
import time
from datetime import date

def search_arxiv(query, start=0, max_results=3000):
    base_url = 'http://export.arxiv.org/api/query?'
    search_query = urllib.parse.quote(query)
    url = f"{base_url}search_query={search_query}&start={start}&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
    response = urllib.request.urlopen(url)
    feed = feedparser.parse(response.read())
    total_results = int(feed.feed.opensearch_totalresults)
    return feed.entries, total_results

def fetch_batch(query, start, batch_size):
    delay = 3
    attempt = 1
    while True:
        try:
            results, _ = search_arxiv(query, start=start, max_results=batch_size)
            if results:
                return results
            print(f"Attempt {attempt}: Empty batch. Retrying...")
        except Exception as e:
            print(f"Attempt {attempt} failed: {str(e)}. Retrying...")
        
        time.sleep(delay)
        delay = min(delay * 2, 60)  # Increase delay for next attempt, max 60 seconds
        attempt += 1

def main():
    query = '(ti:robust*) AND (cat:cs.AI OR cat:cs.LG) AND submittedDate:[2022-01-01 TO 2024-06-30]'
    
    all_data = {}

    print("\nProcessing query:")
    _, total_results = search_arxiv(query, max_results=1)
    print(f"Total number of papers found: {total_results}")

    batch_size = 1000
    batch_count = 0
    for start in range(0, total_results, batch_size):
        print(f"Fetching results {start+1} to {min(start+batch_size, total_results)}...")
        results = fetch_batch(query, start, batch_size)
        
        if results:
            print(f"First paper in batch: {results[0].title}")
            print(f"Last paper in batch: {results[-1].title}")
        
        for paper in results:
            if '2022-01-01' <= paper.published[:10] <= '2024-06-30':
                arxiv_id = paper.id.split('/abs/')[-1]
                all_data[arxiv_id] = {
                    'Title': paper.title,
                    'Authors': ', '.join(author.name for author in paper.authors),
                    'Abstract': paper.summary,
                    'arXiv ID': arxiv_id,
                    'PDF_Link': f"https://arxiv.org/pdf/{arxiv_id}"
                }
        
        batch_count += 1
        if batch_count % 1 == 0:
            input(f"Completed {batch_count} batches. Press Enter to continue...")
        else:
            time.sleep(3)  # Regular pause between batches

    df = pd.DataFrame(list(all_data.values()))
    print(f"\nRetrieved {len(df)} papers:")
    print(df)

    # Save to CSV
    today = date.today().strftime("%b_%d")
    csv_filename = f'robust_{today}.csv'
    df.to_csv(csv_filename, index=False)
    print(f"\nData saved to {csv_filename}")

if __name__ == "__main__":
    main()