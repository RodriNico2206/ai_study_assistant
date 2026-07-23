import argparse
import json
import os
import sys
import time
from pypdf import PdfReader
import pytesseract
from pdf2image import convert_from_path
from ai_study_assistant.config import Config
from ai_study_assistant.generator import NotesGenerator
from ai_study_assistant.web_extractor import WebExtractor

KEYWORDS_GRAFICOS = ["figura", "gráfico", "grafico", "diagrama", "tabla", "ilustración", "fuente:"]

def has_graphic_content(page_pdf, page_text: str) -> bool:
    """Detects if a page contains charts or diagrams based on internal images or text keywords."""
    if hasattr(page_pdf, "images") and len(page_pdf.images) > 0:
        return True
    
    text_lower = page_text.lower()
    if any(kw in text_lower for kw in KEYWORDS_GRAFICOS):
        return True

    return False

def process_pdf_by_batches(input_file_path: str, batch_size: int):
    """Reads PDF and yields batch payloads, auto-detecting pages with graphic elements."""
    reader = PdfReader(input_file_path)
    total_pages = len(reader.pages)
    
    current_batch_text = []
    pdf_images = None
    
    for i, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        
        if len(page_text.strip()) < 10:
            if pdf_images is None:
                print("        [OCR System] Rendering PDF pages into images...")
                pdf_images = convert_from_path(input_file_path, dpi=200)
            
            page_text = pytesseract.image_to_string(pdf_images[i], lang='spa')
            
        is_visual = has_graphic_content(page, page_text)
        
        if is_visual:
            if pdf_images is None:
                pdf_images = convert_from_path(input_file_path, dpi=200)
            
            yield {
                "type": "vision",
                "image": pdf_images[i],
                "text": page_text,
                "start_page": i + 1,
                "end_page": i + 1
            }
        else:
            if page_text.strip():
                current_batch_text.append(f"--- [Page {i+1}] ---\n{page_text}")
            
            if (i + 1) % batch_size == 0 or (i + 1) == total_pages:
                if current_batch_text:
                    start_p = i + 1 - len(current_batch_text) + 1
                    end_p = i + 1
                    yield {
                        "type": "text",
                        "text": "\n".join(current_batch_text),
                        "start_page": start_p,
                        "end_page": end_p
                    }
                    current_batch_text = []

def run_assistant_on_pdf(input_file_path: str, custom_instructions: str = "") -> list[str]:
    """Runs Map phase on a single PDF file and returns list of generated partial notes."""
    generator = NotesGenerator()
    notes = []
    
    print(f"Reading file: {input_file_path}...")
    for payload in process_pdf_by_batches(input_file_path, batch_size=Config.BATCH_SIZE):
        start_page = payload["start_page"]
        end_page = payload["end_page"]
        
        if payload["type"] == "vision":
            print(f" -> [Vision Model: {Config.VISION_MODEL_NAME}] Processing page {start_page}...")
            batch_notes = generator.generate_summary_from_image(
                page_image=payload["image"],
                page_text=payload["text"],
                custom_instructions=custom_instructions
            )
        else:
            print(f" -> [Text Model: {Config.MODEL_NAME}] Processing text pages {start_page} to {end_page}...")
            batch_notes = generator.generate_summary(payload["text"], custom_instructions)
        
        notes.append(f"### Section Notes (Pages {start_page}-{end_page})\n\n{batch_notes}\n\n---\n")
        time.sleep(2)
        
    return notes

def run_assistant(input_file_path: str = None, urls: list = None, custom_instructions: str = ""):
    """Orchestrates Map-Reduce across local PDFs or Web URLs."""
    generator = NotesGenerator()
    all_notes = []
    output_base_name = "summary"

    # CASE A: Process Web URLs
    if urls:
        print(f"--- Processing {len(urls)} Web URL entry point(s) ---")
        output_base_name = "web_documentation"
        target_urls = []
        
        for u in urls:
            sub_urls = WebExtractor.get_menu_urls(u)
            target_urls.extend(sub_urls)
            
        unique_urls = list(dict.fromkeys(target_urls))
        print(f" -> Found {len(unique_urls)} page(s) in navigation tree to process.")

        for i, target_url in enumerate(unique_urls, 1):
            print(f"\n -> [{i}/{len(unique_urls)}] Fetching and rendering web page: {target_url}")
            temp_pdf_path = WebExtractor.url_to_pdf(target_url)
            
            try:
                page_notes = run_assistant_on_pdf(temp_pdf_path, custom_instructions)
                all_notes.extend(page_notes)
            finally:
                if os.path.exists(temp_pdf_path):
                    os.remove(temp_pdf_path)  # Cleanup temp file

    # CASE B: Process Local PDF File
    elif input_file_path:
        output_base_name = os.path.splitext(os.path.basename(input_file_path))[0]
        all_notes = run_assistant_on_pdf(input_file_path, custom_instructions)
        
    else:
        raise ValueError("Neither 'input_path' nor 'urls' were provided in configuration.")

    # REDUCE PHASE
    print(f"\n--- Starting Hierarchical Reduce Phase (Model: {Config.REDUCE_MODEL_NAME}) ---")
    reduction_chunk_size = 4
    intermediate_summaries = []
    
    print(f" -> Processing {len(all_notes)} partial notes in chunks of {reduction_chunk_size}...")
    for i in range(0, len(all_notes), reduction_chunk_size):
        chunk_bundle = all_notes[i : i + reduction_chunk_size]
        bundle_string = "\n".join(chunk_bundle)
        
        chunk_index = (i // reduction_chunk_size) + 1
        print(f"   -> Synthesizing intermediate chunk {chunk_index}...")
        
        intermediate_res = generator.reduce_summaries(bundle_string)
        intermediate_summaries.append(intermediate_res)
        time.sleep(5)

    print(" -> Generating final global overview from intermediate synthesis...")
    final_input_string = "\n\n".join(intermediate_summaries)
    global_summary = generator.reduce_summaries(final_input_string)

    # OUTPUT SAVING
    final_document = f"# Complete Study Guide: Global Summary\n\n{global_summary}\n"
    
    output_dir = os.path.join(os.getcwd(), "summaries")
    os.makedirs(output_dir, exist_ok=True)
    
    output_file_path = os.path.join(output_dir, f"{output_base_name}_global_summary.md")
    
    print(f"Saving global overview to: {output_file_path}...")
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(final_document)
        
    print("Global study guide generated successfully.")

def main():
    """CLI entry point for the application."""
    parser = argparse.ArgumentParser(description="CLI Tool for AI Study Assistant")
    parser.add_argument("--config", required=True, help="Path to the JSON configuration file")
    args = parser.parse_args()
    
    if not os.path.exists(args.config):
        print(f"Error: Configuration file not found at {args.config}", file=sys.stderr)
        sys.exit(1)
        
    try:
        with open(args.config, "r", encoding="utf-8") as f:
            params = json.load(f)
    except json.JSONDecodeError:
        print(f"Error: Failed to parse JSON from {args.config}", file=sys.stderr)
        sys.exit(1)
        
    Config.load_from_dict(params)
    
    try:
        Config.validate()
    except ValueError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    
    try:
        run_assistant(
            input_file_path=params.get("input_path"),
            urls=Config.URLS,
            custom_instructions=params.get("custom_instructions", "")
        )
    except Exception as e:
        print(f"An error occurred during execution: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()