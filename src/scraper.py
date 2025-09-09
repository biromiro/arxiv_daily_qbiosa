import arxiv
from arxiv2text import arxiv_to_md
import logging
from datetime import date, timedelta, datetime, timezone
from typing import List, Dict, Optional, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fetch_peptide_related_papers(
    categories: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    max_results: int = 500,
    specified_date: Optional[date] = None
) -> List[Dict[str, Any]]:
    """
    Fetch peptide/self-assembly/aggregation-related papers from arXiv.

    Args:
        categories (List[str], optional): arXiv categories to search in.
            Defaults to ["q-bio.BM", "cs.LG", "physics.chem-ph", "q-bio.QM"].
        keywords (List[str], optional): Keywords to include in search query.
            Defaults to ["peptide", "self-assembly", "aggregation", "dataset", "machine learning"].
        max_results (int): Maximum number of results to retrieve.
        specified_date (date, optional): Restrict to submissions on this UTC date.

    Returns:
        List[Dict[str, Any]]: Metadata for matching papers.
    """
    if categories is None:
        categories = ["q-bio.BM", "cs.LG", "physics.chem-ph", "q-bio.QM"]

    if keywords is None:
        keywords = ["peptide", "self-assembly", "assembly", "co-assembly", "supramolecular"]

    if specified_date is None:
        specified_date = datetime.now(timezone.utc).date()
        logging.info(f"No date specified, defaulting to {specified_date.strftime('%Y-%m-%d')} UTC.")
    else:
        logging.info(f"Fetching papers for {specified_date.strftime('%Y-%m-%d')} UTC.")

    # Adjust for arXiv submission time (approx.)
    specified_dt = datetime.combine(specified_date, datetime.min.time())
    specified_dt = specified_dt - timedelta(hours=6)

    start_time = specified_dt - timedelta(days=1)
    start_time_str = start_time.strftime('%Y%m%d%H%M')
    end_time_str = specified_dt.strftime('%Y%m%d%H%M')

    # Construct combined query
    category_part = " OR ".join([f"cat:{c}" for c in categories])
    keyword_part = " OR ".join([f"all:{k}" for k in keywords])
    query = f"({category_part}) AND ({keyword_part}) AND submittedDate:[{start_time_str} TO {end_time_str}]"
    logging.info(f"Using arXiv query: {query}")

    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )

    papers: List[Dict[str, Any]] = []
    try:
        results = client.results(search)
        for result in results:
            papers.append({
                'title': result.title,
                'summary': result.summary.strip(),
                'url': result.entry_id,
                'published_date': result.published,
                'updated_date': result.updated,
                'categories': result.categories,
                'authors': [author.name for author in result.authors],
                'pdf_url': result.links[1].href if len(result.links) > 1 else None,
            })
        logging.info(f"Fetched {len(papers)} papers for {specified_date.strftime('%Y-%m-%d')}.")

    except Exception as e:
        logging.error(f"Error during arXiv search: {e}", exc_info=True)

    return papers

if __name__ == '__main__':
    example_date = date.today() - timedelta(days=2)
    papers = fetch_peptide_related_papers(specified_date=example_date)
    print(f"Found {len(papers)} papers on {example_date}:")
    for i, p in enumerate(papers[:10]):
        print(f"{i+1}. {p['title']}")
