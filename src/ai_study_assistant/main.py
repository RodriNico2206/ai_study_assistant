import argparse
import json
import os
import sys
import time
from pypdf import PdfReader
from ai_study_assistant.config import Config
from ai_study_assistant.generator import NotesGenerator

def process_pdf_by_batches(input_file_path: str, batch_size: int) -> str:
    """Reads the PDF file and yields chunks of text combined from 'batch_size' pages."""
    reader = PdfReader(input_file_path)
    total_pages = len(reader.pages)
    
    current_batch_text = []
    
    for i, page in enumerate(reader.pages):
        page_text = page.extract_text()
        if page_text:
            current_batch_text.append(f"--- [Page {i+1}] ---\n{page_text}")
        
        # If the batch size is reached or it is the last page, yield the accumulated chunk
        if (i + 1) % batch_size == 0 or (i + 1) == total_pages:
            if current_batch_text:
                yield "\n".join(current_batch_text), (i + 1 - len(current_batch_text) + 1), (i + 1)
                current_batch_text = []

def run_assistant(input_file_path: str, custom_instructions: str = ""):
    """Orchestrates a hierarchical Map-Reduce process to handle large documents within free tier token limits."""
    # Basic extension validation
    ext = os.path.splitext(input_file_path)[1].lower()
    if ext != ".pdf":
        raise ValueError("This batch processing optimization currently only supports .pdf files.")

    print(f"Reading and splitting file: {input_file_path}...")
    print(f"Configured batch size: {Config.BATCH_SIZE} pages per API request.")
    
    generator = NotesGenerator()
    all_notes = []
    
    # 1. MAP PHASE: Process the PDF using the dynamically configured BATCH_SIZE
    print(f"--- Starting Map Phase (Model: {Config.MODEL_NAME}) ---")
    for chunk_text, start_page, end_page in process_pdf_by_batches(input_file_path, batch_size=Config.BATCH_SIZE):
        print(f" -> Processing pages {start_page} to {end_page}...")
        
        # Send the current text fragment to Groq
        batch_notes = generator.generate_summary(chunk_text, custom_instructions)
        
        # Append a visual Markdown header to separate the processed page ranges
        all_notes.append(f"### Section Notes (Pages {start_page}-{end_page})\n\n{batch_notes}\n\n---\n")
        
        # Safety delay of 2 seconds between calls to mitigate RPM limits on larger documents
        time.sleep(2)

    # 2. HIERARCHICAL REDUCE PHASE: Chunk sub-summaries to avoid token ceiling
    print(f"--- Starting Hierarchical Reduce Phase (Model: {Config.REDUCE_MODEL_NAME}) ---")
    
    # Bundling 4 sub-summaries keeps the batch size safely under the 12,000 TPM limit
    reduction_chunk_size = 4
    intermediate_summaries = []
    
    print(f" -> Processing {len(all_notes)} partial notes in chunks of {reduction_chunk_size}...")
    for i in range(0, len(all_notes), reduction_chunk_size):
        chunk_bundle = all_notes[i : i + reduction_chunk_size]
        bundle_string = "\n".join(chunk_bundle)
        
        chunk_index = (i // reduction_chunk_size) + 1
        print(f"   -> Synthesizing intermediate chunk {chunk_index}...")
        
        # Process the fractioned sub-summaries
        intermediate_res = generator.reduce_summaries(bundle_string)
        intermediate_summaries.append(intermediate_res)
        
        # Extended 5-second safety cooldown to let the TPM bucket refresh completely
        time.sleep(5)

    # Final reduction tier: consolidate the partial synthesis blocks into the final overview
    print(" -> Generating final global overview from intermediate synthesis...")
    final_input_string = "\n\n".join(intermediate_summaries)
    global_summary = generator.reduce_summaries(final_input_string)

    # 3. CONSOLIDATE FINAL DOCUMENT (Purely Global Version)
    final_document = (
        f"# Complete Study Guide: Global Summary\n\n"
        f"{global_summary}\n"
    )
    
    base_name = os.path.splitext(os.path.basename(input_file_path))[0]
    output_file_name = f"{base_name}_global_summary.md"
    
    # Definimos la ruta de la carpeta 'summaries' en la raíz del proyecto
    project_root = os.getcwd()
    output_dir = os.path.join(project_root, "summaries")
    
    # Creamos la carpeta automáticamente si no existe
    os.makedirs(output_dir, exist_ok=True)
    
    # Construimos la ruta final dentro de esa carpeta
    output_file_path = os.path.join(output_dir, output_file_name)
    
    print(f"Saving global overview to: {output_file_path}...")
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(final_document)
        
    print("Global study guide generated successfully.")

def main():
    """CLI entry point for the application."""
    parser = argparse.ArgumentParser(description="CLI Tool for AI Study Assistant")
    parser.add_argument(
        "--config", 
        required=True, 
        help="Path to the JSON configuration file"
    )
    
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
        
    if "input_path" not in params or not params["input_path"]:
        print("Error: Missing required parameter 'input_path' in JSON file.", file=sys.stderr)
        sys.exit(1)
            
    # Load parameters from JSON configuration data
    Config.load_from_dict(params)
    
    try:
        Config.validate()
    except ValueError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    
    try:
        run_assistant(
            input_file_path=params["input_path"],
            custom_instructions=params.get("custom_instructions", "")
        )
    except Exception as e:
        print(f"An error occurred during execution: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()