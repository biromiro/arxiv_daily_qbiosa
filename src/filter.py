import os
import requests
import json
import logging
import re
from arxiv2text import arxiv_to_md

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "google/gemini-2.0-flash-001"


def call_openrouter_api(prompt: str, max_tokens: int = 5) -> str | None:
    """Call OpenRouter API and return response text."""
    if not OPENROUTER_API_KEY:
        logging.error("OPENROUTER_API_KEY not set.")
        return None

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }

    try:
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content'].strip()
    except Exception as e:
        logging.error(f"OpenRouter API call failed: {e}", exc_info=True)
        return None


def filter_papers_by_topic(papers: list, topic: str = None) -> list:
    """
    Filter papers to keep only those relevant to peptide self-assembly / aggregation /
    peptide datasets / ML for biomolecules.
    """

    if topic is None:
        topic = "peptide self-assembly, aggregation or co-assembly, or machine learning for peptides/biomolecules"

    if not OPENROUTER_API_KEY:
        logging.warning("No API key set. Falling back to stricter keyword filtering.")

        core_terms = ["peptide", "protein", "biomolecule", "polypeptide", "supramolecular"]
        assembly_terms = ["self-assembly", "co-assembly", "aggregation", "assembly"]
        optional_terms = ["dataset", "simulation", "screening"]

        filtered = []
        for paper in papers:
            text = (paper.get("title", "") + " " + paper.get("summary", "")).lower()

            has_core = any(term in text for term in core_terms)
            has_assembly = any(term in text for term in assembly_terms)
            has_optional = any(term in text for term in optional_terms)

            # Keep only if both peptide/protein context + assembly context
            if has_core and has_assembly:
                filtered.append(paper)
                logging.info(f"[KEEP] {paper.get('title', '')[:60]}...")
            elif has_core and has_optional:
                # Allow peptide + dataset/simulation papers even without explicit 'assembly'
                filtered.append(paper)
                logging.info(f"[KEEP-OPTIONAL] {paper.get('title', '')[:60]}...")
            else:
                logging.debug(f"[DROP] {paper.get('title', '')[:60]}...")

        logging.info(f"Keyword filter retained {len(filtered)} of {len(papers)} papers.")
        return filtered

    # --- If API key is available, use LLM-based filtering ---
    filtered_papers = []
    logging.info(f"Filtering {len(papers)} papers with OpenRouter (topic: '{topic}')...")

    for i, paper in enumerate(papers):
        title = paper.get("title", "N/A")
        summary = paper.get("summary", "N/A")
        full_text = paper.get("full_text", "N/A")
        prompt = (
            f"On a scale from 0 (not relevant) to 10 (highly relevant), "
            f"how relevant is this paper to research in '{topic}'? "
            f"Output only an integer.\n\nTitle: {title}\nAbstract: {summary}\n\nFull Text: {full_text[:10000]}"
        )
        ai_response = call_openrouter_api(prompt, max_tokens=5)

        try:
            score = int(ai_response.strip().split()[0])
        except:
            score = 0

        if score >= 6:
            filtered_papers.append(paper)
            logging.info(f"[KEEP] {i+1}/{len(papers)}: {title[:100]}...")
        else:
            logging.info(f"[DROP] {i+1}/{len(papers)}: {title[:100]}...")

    logging.info(f"Filtering complete: kept {len(filtered_papers)} / {len(papers)} papers.")
    return filtered_papers


rating_prompt_template = """
# Role
You are an experienced researcher in machine learning for biomolecules and peptide self-assembly, skilled at quickly evaluating the potential value of research papers.

# Task
Based on the paper's title and abstract, summarize it and score it across multiple dimensions (1-10 points, 1 being the lowest, 10 being the highest). 
Finally, provide an overall preliminary priority score.

# Input
Paper Title: %s
Paper Abstract: %s
Paper Full Text: %s

# My Research Interests
- Peptide self-assembly, co-assembly, and aggregation
- Machine learning for peptides and biomolecules
- Datasets for peptide structure, aggregation or assembly
- Computational screening or simulation of structure or assembly/aggregation of peptides

# Output Requirements
Output must be valid JSON (RFC8259). Please output the evaluation and explanations in the following JSON format:

{
  "tldr": "<short summary in English>",
  "explanation": "<detailed explanation in English>",
  "interests_alignment": "<explanation of alignment with my research interests in English>",
  "relevance_score": <int>,
  "novelty_claim_score": <int>,
  "clarity_score": <int>,
  "potential_impact_score": <int>,
  "overall_priority_score": <int>
}

# Scoring Guidelines
- Relevance: Focus on whether it is directly related to the research interests I provided.
- Novelty: Evaluate the degree of innovation claimed in the abstract regarding the method or viewpoint compared to known work.
- Clarity: Evaluate whether the abstract itself is easy to understand and complete with essential elements.
- Potential Impact: Evaluate the importance of the problem it claims to solve and the potential application value of the results.
- Overall Priority: Provide an overall score combining all the above factors. A high score indicates suggested priority for reading.
"""


def rate_papers(papers: list) -> list:
    """Rate peptide/assembly papers with OpenRouter model."""
    if not OPENROUTER_API_KEY:
        logging.warning("No API key set. Skipping rating.")
        return papers

    logging.info(f"Scoring {len(papers)} papers...")
    for i, paper in enumerate(papers):
        title = paper.get("title", "N/A")
        summary = paper.get("summary", "N/A")
        
        link = paper.get("pdf_url", None)
        full_text = "N/A"
        if link is not None:
            try:
                full_text = arxiv_to_md(link, output_folder="./temp_texts")
            except:
                logging.warning(f"Paper {i+1}: failed to extract full text from {link}.", exc_info=True)
        
        prompt = rating_prompt_template % (title, summary, full_text)

        ai_response = call_openrouter_api(prompt, max_tokens=800)
        if not ai_response:
            logging.warning(f"Paper {i+1}: no response.")
            continue

        try:
            if "```json" in ai_response:
                ai_response = ai_response.split("```json")[1].split("```")[0]
            rating_data = json.loads(ai_response)
            paper.update(rating_data)
            logging.info(f"Paper {i+1}: scored successfully.")
        except Exception as e:
            logging.error(f"Paper {i+1}: failed to parse rating. Raw: {ai_response[:100]}...", exc_info=True)

    return papers