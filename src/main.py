import os
import json
import logging
import argparse
from datetime import date, datetime, timedelta

from scraper import fetch_peptide_related_papers
from filter import filter_papers_by_topic, rate_papers
from html_generator import generate_html_from_json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_JSON_DIR = os.path.join(PROJECT_ROOT, 'daily_json')
DEFAULT_HTML_DIR = os.path.join(PROJECT_ROOT, 'daily_html')
DEFAULT_TEMPLATE_DIR = os.path.join(PROJECT_ROOT, 'templates')
DEFAULT_TEMPLATE_NAME = 'paper_template.html'

def main(target_date: date):
    """Pipeline: fetch peptide/self-assembly papers, filter, save, and generate HTML report."""
    logging.info(f"=== Processing date: {target_date.isoformat()} ===")

    json_filename = f"{target_date.isoformat()}.json"
    json_filepath = os.path.join(DEFAULT_JSON_DIR, json_filename)

    if os.path.exists(json_filepath):
        logging.info(f"Found existing JSON: {json_filepath}. Skipping fetch.")
    else:
        logging.info("Fetching new peptide/self-assembly papers...")
        raw_papers = fetch_peptide_related_papers(specified_date=target_date)

        if not raw_papers:
            logging.warning(f"No papers found for {target_date.isoformat()}.")
            return

        logging.info(f"Fetched {len(raw_papers)} raw papers.")

        logging.info("Filtering and scoring papers...")
        filtered_papers = filter_papers_by_topic(
            raw_papers,
            topic="peptide self-assembly, co-assembly, aggregation, peptide datasets, machine learning for biomolecules"
        )
        filtered_papers = rate_papers(filtered_papers)
        filtered_papers.sort(key=lambda x: x.get('overall_priority_score', 0), reverse=True)

        for paper in filtered_papers:
            if isinstance(paper.get('published_date'), datetime):
                paper['published_date'] = paper['published_date'].isoformat()
            if isinstance(paper.get('updated_date'), datetime):
                paper['updated_date'] = paper['updated_date'].isoformat()

        os.makedirs(DEFAULT_JSON_DIR, exist_ok=True)
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(filtered_papers, f, indent=4, ensure_ascii=False)
        logging.info(f"Saved filtered papers to {json_filepath}")

    logging.info("Generating HTML report...")
    if not os.path.exists(json_filepath):
        logging.error(f"Cannot find {json_filepath} to generate HTML.")
        return

    try:
        generate_html_from_json(
            json_file_path=json_filepath,
            template_dir=DEFAULT_TEMPLATE_DIR,
            template_name=DEFAULT_TEMPLATE_NAME,
            output_dir=DEFAULT_HTML_DIR
        )
        logging.info(f"Report generated in {DEFAULT_HTML_DIR}")

        reports_json_path = os.path.join(PROJECT_ROOT, 'reports.json')
        html_files = [f for f in os.listdir(DEFAULT_HTML_DIR) if f.endswith('.html')]
        html_files.sort(reverse=True)
        with open(reports_json_path, 'w', encoding='utf-8') as f:
            json.dump(html_files, f, indent=4, ensure_ascii=False)
        logging.info(f"Updated reports.json with {len(html_files)} entries.")

    except Exception as e:
        logging.error(f"Error during HTML generation: {e}", exc_info=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fetch/filter/generate reports on peptide/self-assembly ML papers.')
    parser.add_argument('--date', type=str, help='Date to fetch (YYYY-MM-DD). Defaults to today UTC.')

    args = parser.parse_args()
    run_date = date.today()
    num_days_to_run = 90

    if args.date:
        try:
            run_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        except ValueError:
            logging.error("Invalid date format, use YYYY-MM-DD.")
            exit(1)

    for offset in range(num_days_to_run - 1, -1, -1):
        main(target_date=run_date - timedelta(days=offset))
