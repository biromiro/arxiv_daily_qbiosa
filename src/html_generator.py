import json
import os
import logging
from datetime import date, datetime, timezone
from jinja2 import Environment, FileSystemLoader


def generate_html_from_json(json_file_path: str, template_dir: str, template_name: str, output_dir: str):
    """Reads paper data from a JSON file and generates an HTML page using a Jinja2 template.

    Args:
        json_file_path: Path to the input JSON file.
        template_dir: Directory containing the Jinja2 template.
        template_name: Name of the Jinja2 template file.
        output_dir: Directory where the generated HTML file will be saved.
    """
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            papers = json.load(f)
            papers.sort(key=lambda x: x.get('overall_priority_score', 0), reverse=True)
    except FileNotFoundError:
        logging.error(f"JSON file not found at {json_file_path}")
        return
    except json.JSONDecodeError:
        logging.error(f"Could not decode JSON from {json_file_path}")
        return

    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template(template_name)

    # Extract date from filename (expecting YYYY-MM-DD.json)
    try:
        filename = os.path.basename(json_file_path)
        date_str = filename.split('.')[0]
        report_date = date.fromisoformat(date_str)  # works with dashes
        formatted_date = report_date.strftime("%Y-%m-%d")  # keep dashes!
        page_title = f"ArXiv Peptide/Assembly Papers - {report_date.strftime('%B %d, %Y')}"
    except (IndexError, ValueError):
        logging.warning(f"Could not extract date from filename {filename}. Using today instead.")
        today = date.today()
        report_date = today
        formatted_date = today.strftime("%Y-%m-%d")
        page_title = f"ArXiv Peptide/Assembly Papers - {today.strftime('%B %d, %Y')}"

    generation_time = datetime.now(timezone.utc)
    html_content = template.render(
        papers=papers,
        title=page_title,
        report_date=report_date,
        generation_time=generation_time
    )

    # HTML output filename now also uses dashes
    output_filename = f"{formatted_date}.html"
    output_filepath = os.path.join(output_dir, output_filename)

    os.makedirs(output_dir, exist_ok=True)

    try:
        with open(output_filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logging.info(f"Successfully generated HTML: {output_filepath}")
    except IOError as e:
        logging.error(f"Error writing HTML file {output_filepath}: {e}")


# Example usage for testing
if __name__ == '__main__':
    dummy_papers = [
        {
            "title": "Awesome Paper 1 on Peptides",
            "summary": "This paper introduces a computational approach for peptide aggregation...",
            "authors": ["Author A", "Author B"],
            "url": "https://arxiv.org/abs/2301.00001"
        },
        {
            "title": "Protein Self-Assembly via Simulation",
            "summary": "Exploring large-scale simulations of protein aggregation...",
            "authors": ["Author C"],
            "url": "https://arxiv.org/abs/2301.00002"
        }
    ]
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dummy_json_dir = os.path.join(project_root, 'daily_json')
    dummy_html_dir = os.path.join(project_root, 'daily_html')
    dummy_template_dir = os.path.join(project_root, 'templates')
    dummy_template_name = 'paper_template.html'

    os.makedirs(dummy_json_dir, exist_ok=True)
    os.makedirs(dummy_html_dir, exist_ok=True)
    os.makedirs(dummy_template_dir, exist_ok=True)

    dummy_template_path = os.path.join(dummy_template_dir, dummy_template_name)
    if not os.path.exists(dummy_template_path):
        with open(dummy_template_path, 'w') as f:
            f.write("<h1>{{ title }}</h1><ul>{% for paper in papers %}<li><a href=\"{{ paper.url }}\">{{ paper.title }}</a>: {{ paper.summary }}</li>{% endfor %}</ul>")

    today_str = date.today().strftime("%Y-%m-%d")  # dashes
    dummy_json_filename = f"{today_str}.json"
    dummy_json_filepath = os.path.join(dummy_json_dir, dummy_json_filename)

    with open(dummy_json_filepath, 'w', encoding='utf-8') as f:
        json.dump(dummy_papers, f, indent=4)

    logging.basicConfig(level=logging.INFO)
    logging.info("Running example generation...")
    generate_html_from_json(
        json_file_path=dummy_json_filepath,
        template_dir=dummy_template_dir,
        template_name=dummy_template_name,
        output_dir=dummy_html_dir
    )
    logging.info("Example generation finished.")
