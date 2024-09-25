import urllib.parse
import urllib.request
import feedparser
import pandas as pd
import time
from datetime import date

def search_arxiv(query, start=0, max_results=100):
    """
    Sends a query to the arXiv API and retrieves a list of papers.

    Parameters:
        query (str): The encoded query string.
        start (int): The starting index for results.
        max_results (int): The maximum number of results to retrieve.

    Returns:
        tuple: A tuple containing a list of entries (papers) and the total number of results.
    """
    base_url = 'http://export.arxiv.org/api/query?'
    url = (
        f"{base_url}search_query={query}&start={start}&"
        f"max_results={max_results}&sortBy=submittedDate&"
        f"sortOrder=descending"
    )
    response = urllib.request.urlopen(url)
    feed = feedparser.parse(response.read())
    total_results = int(feed.feed.opensearch_totalresults)
    return feed.entries, total_results

def fetch_batch(query, start, batch_size):
    """
    Fetches a batch of results with retry logic and exponential backoff.

    Parameters:
        query (str): The encoded query string.
        start (int): The starting index for results.
        batch_size (int): The number of results to fetch.

    Returns:
        list: A list of results (papers) if successful, or an empty list after exhausting attempts.
    """
    max_attempts = 100  # Maximum number of attempts to fetch the batch
    delay = 3           # Initial delay between attempts
    attempt = 0
    while attempt < max_attempts:
        try:
            results, _ = search_arxiv(query, start=start, max_results=batch_size)
            if results:
                return results
            else:
                print(f"Attempt {attempt + 1}: Empty batch. Retrying...")
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {str(e)}. Retrying...")
        attempt += 1
        time.sleep(delay)
        delay = min(delay * 2, 60)  # Exponential backoff up to 60 seconds
    print(f"Failed to fetch batch after {max_attempts} attempts.")
    return []

def construct_query(term):
    """
    Constructs the query string for a given search term.

    Parameters:
        term (str): The search term.

    Returns:
        str: The constructed query string.
    """
    if ' ' in term:
        # For phrases, wrap in quotes to search for the exact phrase in the title
        return f'ti:"{term}"'
    else:
        # For single words, search for that word in the title
        return f'ti:{term}'

def main():
    # List of search terms with expanded variations
    search_terms = [
        
        # I'm not sure how ArXiv handles wildcards so I wrote
        # them out manually instead.
        
        # Variations for "align*"
        "align", "alignment", "aligned",
        
        # Variations for "misalign*"
        "misalign", "misalignment",
        
        # Variations for "safe*"
        "safe", "safety", "safely",
        
        # Variations for "robust*"
        "robust", "robustness", "robustly"
        
        # Variations for "interpret*"
        "interpret", "interpretable", "interpretability",
        
        # Variations for "automat*"
        "automated alignment", "automated safety",
        
        # Variations for "unlearn*"
        "unlearn", "unlearning",
        
        # Variations for "evaluat*"
        "evaluate", "evaluation",
        
        # Variations for "honest*"
        "honest", "honesty", "honestly",
        
        # Variations for "model organism*"
        "Model organism", "model organisms",
        
        # Variations for "power seeking"
        "power seeking", "seek power",
        
        # Variations for "enhancing human feedback"
        "human feedback", "enhanced feedback", "enhancing feedback",
        
        # Variations for "collu*"
        "collusion", "collude", "colluding",
        
        # Variations for "guaranteed safe AI"
        "safe by design", "guaranteed safe",

        # Individual other terms
        "multiagent",
        "brain emulation",
        "agent foundations",
        "scalable oversight"
    ]

    # Base query components: categories and corrected date ranges
    categories = "(cat:cs.AI OR cat:cs.LG)"
    # Corrected date ranges without hyphens and covering full years
    date_ranges = [
        "submittedDate:[20220101 TO 20221231]",
        "submittedDate:[20230101 TO 20231231]",
        "submittedDate:[20240101 TO 20250101]",
    ]

    # Initialize data structures
    all_data = {}      # Dictionary to store all retrieved paper data
    duplicates = set() # Set to track duplicate arXiv IDs

    # Load existing data from CSV if checkpoint exists
    today = date.today().strftime("%b_%d")
    csv_filename = f'data_{today}.csv'
    try:
        existing_df = pd.read_csv(csv_filename)
        existing_ids = set(existing_df['arXiv ID'].tolist())
        print(f"Loaded {len(existing_df)} existing records from {csv_filename}.")
    except FileNotFoundError:
        existing_df = pd.DataFrame()
        existing_ids = set()
        print("No existing checkpoint found. Starting fresh.")

    total_papers_to_retrieve = 0  # Total number of papers to retrieve across all terms
    total_papers_retrieved = 0    # Total number of papers actually retrieved

    # Process each search term
    for term in search_terms:
        print(f"\nProcessing term: {term}")
        query_term = construct_query(term)
        term_total_results = 0  # Total results across all date ranges for this term

        # Construct the full query with the entire date range
        full_query = f'({query_term}) AND {categories} AND submittedDate:[20220101 TO 20250101]'
        encoded_query = urllib.parse.quote(full_query)
        _, total_results = search_arxiv(encoded_query, max_results=1)
        print(f"Total number of papers found for term '{term}': {total_results}")

        # Check if total_results exceeds API limitations (usually around 1000)
        if total_results > 1000:
            print("Total results exceed 1000. Splitting the query into yearly ranges to avoid API limitations.")
            # Process each year separately
            for date_range in date_ranges:
                yearly_query = f'({query_term}) AND {categories} AND {date_range}'
                encoded_yearly_query = urllib.parse.quote(yearly_query)
                print(f"\nProcessing date range: {date_range}")
                print(f"Query: {urllib.parse.unquote(yearly_query)}")
                _, yearly_total_results = search_arxiv(encoded_yearly_query, max_results=1)
                print(f"Total number of papers found: {yearly_total_results}")

                if yearly_total_results == 0:
                    continue  # Skip if no results for this year

                num_papers_to_retrieve = yearly_total_results
                total_papers_to_retrieve += num_papers_to_retrieve
                term_total_results += num_papers_to_retrieve

                batch_size = 100  # Maximum batch size per API request
                papers_retrieved_for_range = 0
                start = 0
                while (
                    papers_retrieved_for_range < num_papers_to_retrieve and start < yearly_total_results
                ):
                    remaining_papers = num_papers_to_retrieve - papers_retrieved_for_range
                    fetch_size = min(batch_size, remaining_papers)
                    print(
                        f"Fetching results {start + 1} to "
                        f"{min(start + fetch_size, yearly_total_results)}..."
                    )
                    results = fetch_batch(encoded_yearly_query, start, fetch_size)

                    if not results:
                        print("No results fetched in this batch.")
                        break  # Break if no results are returned

                    for paper in results:
                        submitted_date = paper.published[:10]
                        # Filter papers submitted after July 31, 2024
                        if submitted_date > '2024-07-31':
                            continue
                        arxiv_id = paper.id.split('/abs/')[-1]
                        if arxiv_id in existing_ids or arxiv_id in all_data:
                            duplicates.add(arxiv_id)
                            continue
                        else:
                            all_data[arxiv_id] = {
                                'Title': paper.title.strip().replace('\n', ' '),
                                'Authors': ', '.join(
                                    author.name for author in paper.authors
                                ),
                                'Abstract': paper.summary.strip().replace('\n', ' '),
                                'arXiv ID': arxiv_id,
                                'PDF_Link': f"https://arxiv.org/pdf/{arxiv_id}",
                                'Submitted': submitted_date
                            }
                            papers_retrieved_for_range += 1
                            total_papers_retrieved += 1

                    # Save checkpoint after each batch to prevent data loss
                    combined_data = list(all_data.values())
                    if not existing_df.empty:
                        combined_df = pd.concat(
                            [existing_df, pd.DataFrame(combined_data)], ignore_index=True
                        )
                    else:
                        combined_df = pd.DataFrame(combined_data)
                    combined_df.drop_duplicates(subset=['arXiv ID'], inplace=True)
                    combined_df.to_csv(csv_filename, index=False)
                    print(f"Checkpoint saved with {len(combined_df)} records.")

                    time.sleep(3)  # Be polite to the API and avoid rate limiting

                    start += fetch_size  # Increment start index for the next batch

                if papers_retrieved_for_range == 0:
                    print(f"No papers retrieved for date range '{date_range}'.")
        else:
            # Total results within API limitations; process normally
            print("Total results within API limit. Processing normally.")
            print(f"Query: {urllib.parse.unquote(full_query)}")
            num_papers_to_retrieve = total_results
            total_papers_to_retrieve += num_papers_to_retrieve
            term_total_results += num_papers_to_retrieve

            batch_size = 100  # Maximum batch size per API request
            papers_retrieved_for_term = 0
            start = 0
            while (
                papers_retrieved_for_term < num_papers_to_retrieve and start < total_results
            ):
                remaining_papers = num_papers_to_retrieve - papers_retrieved_for_term
                fetch_size = min(batch_size, remaining_papers)
                print(
                    f"Fetching results {start + 1} to "
                    f"{min(start + fetch_size, total_results)}..."
                )
                results = fetch_batch(encoded_query, start, fetch_size)

                if not results:
                    print("No results fetched in this batch.")
                    break  # Break if no results are returned

                for paper in results:
                    submitted_date = paper.published[:10]
                    # Filter papers submitted after July 31, 2024
                    if submitted_date > '2024-07-31':
                        continue
                    arxiv_id = paper.id.split('/abs/')[-1]
                    if arxiv_id in existing_ids or arxiv_id in all_data:
                        duplicates.add(arxiv_id)
                        continue
                    else:
                        all_data[arxiv_id] = {
                            'Title': paper.title.strip().replace('\n', ' '),
                            'Authors': ', '.join(
                                author.name for author in paper.authors
                            ),
                            'Abstract': paper.summary.strip().replace('\n', ' '),
                            'arXiv ID': arxiv_id,
                            'PDF_Link': f"https://arxiv.org/pdf/{arxiv_id}",
                            'Submitted': submitted_date
                        }
                        papers_retrieved_for_term += 1
                        total_papers_retrieved += 1

                # Save checkpoint after each batch to prevent data loss
                combined_data = list(all_data.values())
                if not existing_df.empty:
                    combined_df = pd.concat(
                        [existing_df, pd.DataFrame(combined_data)], ignore_index=True
                    )
                else:
                    combined_df = pd.DataFrame(combined_data)
                combined_df.drop_duplicates(subset=['arXiv ID'], inplace=True)
                combined_df.to_csv(csv_filename, index=False)
                print(f"Checkpoint saved with {len(combined_df)} records.")

                time.sleep(3)  # Be polite to the API and avoid rate limiting

                start += fetch_size  # Increment start index for the next batch

            if papers_retrieved_for_term == 0:
                print(f"No papers retrieved for term '{term}'.")

        print(f"Total papers retrieved for term '{term}': {term_total_results}")

    print(
        f"\nRetrieved a total of {total_papers_retrieved} papers out of "
        f"{total_papers_to_retrieve} available."
    )

    # Save final data after processing all terms
    combined_data = list(all_data.values())
    if not existing_df.empty:
        combined_df = pd.concat(
            [existing_df, pd.DataFrame(combined_data)], ignore_index=True
        )
    else:
        combined_df = pd.DataFrame(combined_data)
    combined_df.drop_duplicates(subset=['arXiv ID'], inplace=True)
    combined_df.to_csv(csv_filename, index=False)
    print(
        f"\nFinal data saved to {csv_filename} with "
        f"{len(combined_df)} unique records."
    )

if __name__ == "__main__":
    main()
