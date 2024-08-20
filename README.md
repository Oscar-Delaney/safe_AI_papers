# Collecting papers to analyze from company websites
We looked at papers published on the websites of Anthropic, (Google) DeepMind, and OpenAI between January 2022 and July 2024. Specifically, we looked in the following places:
* All papers published on https://www.anthropic.com/research
* All papers available from https://deepmind.google/research/publications/ and https://web.archive.org/web/20220626233857/https://www.deepmind.com/research. [^1]
* Papers on https://openai.com/research, using the website filters to show only papers that are likely to be relevant.[^2]

We ignored results on these pages that did not link to a paper (e.g. blog posts). We used collecting_abstracts.py to automate part of the process of adding information about the papers that we had identified to our dataset.

# Collecting papers to analyze from arXiv
To collect relevant papers from arXiv, we used the following approach:
* Using the arXiv API to search for all papers meeting the following criteria. (1) Published in the relevant timeframe, (2) Listed on arXiv in the categories relating to artificial intelligence (cs.AI) or machine learning (cs.LG), and (3) At least one term in the title that is relevant to safe AI development. The terms that we searched for are: align*, misalign*, safe*, robust*, powerseeking, seek power, multiagent, model organism*, safe* by design, brain emulation, interpretab*, honest, automat* alignment, automat* safety, human feedback, enhanc* feedback. Terms around alignment and safety are often used when discussing safe AI development in general. The other terms are derived from the names of the research areas in our paper.
* We then used an automated process to filter only to papers where the first author lists an affiliation at Anthropic, (Google) DeepMind, or OpenAI. (The arXiv search function does not provide a way to filter by affiliation, meaning that the list from the previous bullet point includes many papers by researchers not at one of these three AI companies.) Specifically, our code checks whether the first page of the paper on arXiv includes one of the strings "Anthropic", "DeepMind", or "OpenAI".[^3] If it does, the text of this first page is passed to language models to identify the institution of the first author.[^4]
* We manually reviewed all the filtered papers to determine whether they should be added to our dataset.

# Categorizing papers
To categorize the papers, one of us (Delaney) read the title and abstract. If the paper seemed relevant to safety, Delaney assigned it to the category that seemed most appropriate.
We used two approaches to minimize classification errors.
* First, another author (Guest) independently categorized a random 25% of the papers.
We discussed cases where our categorisations differed and Delaney did another round of categorizations taking the discussion into account.
* Second, in assessing_papers.py we used the GPT-4o-mini API by providing descriptions of our clusters to the API and asking it to classify each paper based on the title and abstract. Delaney reviewed any cases where the API gave a different answer to him, updating the categorization as appropriate. There were 34 papers (out of 359 for which we had an abstract and the API assessment worked) where GPT-4o-mini disagreed with Delaney, and of these based on both Delaney and Guest reviewing them, in five cases we did change our initial categorization.

[^1]: Much of DeepMind’s research from before the merger with Google Brain is no longer available on the live website, hence we also used the Internet Archive.
We did not include pre-merger Google Brain research.
[^2]: Specifically, we looked at any paper that matched the following filters: "adversarial examples", "human feedback", "interpretability", "multi-agent", "robustness", "safety & alignment".
There is also a filter for “responsible AI”, but all papers in this category are either more about governance than technical safety and so out of scope or already included because of the other filters.
[^3]: These strings would appear in the first page of the article both if an author lists their institution as Anthropic, DeepMind, or OpenAI,, but also if the authors mention these organizations for some other reason.
[^4]: There are two language model steps. First Claude 3.5 Sonnet produces a longer answer ('The affiliation of the first author is DeepMind') which is then summarized by Claude 3 Haiku ('DeepMind').
