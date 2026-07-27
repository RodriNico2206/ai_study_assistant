import argparse, json, os, re, sys, time
from pypdf import PdfReader
from pdf2image import convert_from_path

from ai_study_assistant.config import Config
from ai_study_assistant.generator import NotesGenerator
from ai_study_assistant.notifier import EmailNotifier


def has_graphic_content(page_pdf, page_text: str) -> bool:
    """Detects if a page contains charts or diagrams based on native embedded images, captions, or empty native text."""
    if hasattr(page_pdf, "images") and len(page_pdf.images) > 0:
        return True

    pattern = r"\b(figura|gráfico|grafico|diagrama|tabla|ilustración)\s*\d+"
    if re.search(pattern, page_text.lower()):
        return True

    # If selectable text is negligible, classify as visual page
    if len(page_text.strip()) < 10:
        return True

    return False


def process_pdf_by_batches(input_file_path: str, batch_size: int):
    """Reads PDF and yields batch payloads, dividing visual pages between Groq Vision API and OpenRouter Vision."""
    reader = PdfReader(input_file_path)
    total_pages = len(reader.pages)

    current_batch_text = []
    pdf_images = None
    vision_calls_count = 0

    print(
        f" -> [Token Budget] Groq Vision limit: {Config.MAX_VISION_PAGES} page(s). "
        f"Overflow visual pages will route to OpenRouter ({Config.OPENROUTER_VISION_MODEL})."
    )

    for i, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        is_visual = has_graphic_content(page, page_text)

        if is_visual:
            if current_batch_text:
                start_p = i + 1 - len(current_batch_text)
                end_p = i
                yield {
                    "type": "text",
                    "text": "\n".join(current_batch_text),
                    "start_page": start_p,
                    "end_page": end_p,
                }
                current_batch_text = []

            if pdf_images is None:
                pdf_images = convert_from_path(
                    input_file_path, dpi=Config.PDF_DPI
                )

            if vision_calls_count < Config.MAX_VISION_PAGES:
                vision_calls_count += 1
                print(
                    f" -> [Quota Manager] Visual content on Page {i+1}. "
                    f"Sending to Groq Vision API ({vision_calls_count}/{Config.MAX_VISION_PAGES})..."
                )
                yield {
                    "type": "groq_vision",
                    "image": pdf_images[i],
                    "text": page_text,
                    "start_page": i + 1,
                    "end_page": i + 1,
                }
            else:
                print(
                    f" -> [Fallback Routing] Visual content on Page {i+1}. "
                    f"Groq limit reached. Routing to OpenRouter Vision ({Config.OPENROUTER_VISION_MODEL})..."
                )
                yield {
                    "type": "openrouter_vision",
                    "image": pdf_images[i],
                    "text": page_text,
                    "start_page": i + 1,
                    "end_page": i + 1,
                }
        else:
            if page_text.strip():
                current_batch_text.append(f"--- [Page {i+1}] ---\n{page_text}")

            if len(current_batch_text) == batch_size or (i + 1) == total_pages:
                if current_batch_text:
                    start_p = i + 1 - len(current_batch_text) + 1
                    end_p = i + 1
                    yield {
                        "type": "text",
                        "text": "\n".join(current_batch_text),
                        "start_page": start_p,
                        "end_page": end_p,
                    }
                    current_batch_text = []


def run_assistant(input_file_path: str, custom_instructions: str = ""):
    """Orchestrates a hierarchical Map-Reduce process supporting text and cloud vision models."""
    ext = os.path.splitext(input_file_path)[1].lower()
    if ext != ".pdf":
        raise ValueError(
            "This batch processing optimization currently only supports .pdf files."
        )

    print(f"Reading and splitting file: {input_file_path}...")
    print(f"Configured batch size: {Config.BATCH_SIZE} pages per text request.")

    generator = NotesGenerator()
    all_notes = []

    # 1. MAP PHASE
    print(f"--- Starting Hybrid Map Phase ---")
    for payload in process_pdf_by_batches(
        input_file_path, batch_size=Config.BATCH_SIZE
    ):
        start_page = payload["start_page"]
        end_page = payload["end_page"]

        if payload["type"] == "groq_vision":
            print(
                f" -> [Groq Vision: {Config.VISION_MODEL_NAME}] Processing page {start_page}..."
            )
            batch_notes = generator.generate_summary_from_image(
                page_image=payload["image"],
                page_text=payload["text"],
                custom_instructions=custom_instructions,
            )
        elif payload["type"] == "openrouter_vision":
            print(
                f" -> [OpenRouter Vision: {Config.OPENROUTER_VISION_MODEL}] Processing page {start_page}..."
            )
            batch_notes = generator.generate_summary_from_openrouter_vision(
                page_image=payload["image"],
                page_text=payload["text"],
                custom_instructions=custom_instructions,
            )
        else:
            print(
                f" -> [Text Model: {Config.MODEL_NAME}] Processing text pages {start_page} to {end_page}..."
            )
            batch_notes = generator.generate_summary(
                payload["text"], custom_instructions
            )

        all_notes.append(
            f"### Section Notes (Pages {start_page}-{end_page})\n\n{batch_notes}\n\n---\n"
        )
        time.sleep(2)

    # 2. HIERARCHICAL REDUCE PHASE
    print(
        f"--- Starting Hierarchical Reduce Phase (Model: {Config.REDUCE_MODEL_NAME}) ---"
    )
    reduction_chunk_size = 4
    intermediate_summaries = []

    print(
        f" -> Processing {len(all_notes)} partial notes in chunks of {reduction_chunk_size}..."
    )
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

    # 3. CONSOLIDATE FINAL DOCUMENT
    final_document = (
        f"# Complete Study Guide: Global Summary\n\n{global_summary}\n"
    )

    base_name = os.path.splitext(os.path.basename(input_file_path))[0]
    output_file_name = f"{base_name}_global_summary.md"

    project_root = os.getcwd()
    output_dir = os.path.join(project_root, "summaries")
    os.makedirs(output_dir, exist_ok=True)

    output_file_path = os.path.join(output_dir, output_file_name)

    print(f"Saving global overview to: {output_file_path}...")
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(final_document)

    print("Global study guide generated successfully.")


def main():
    """CLI entry point for the application."""
    parser = argparse.ArgumentParser(description="CLI Tool for AI Study Assistant")
    parser.add_argument(
        "--config", required=True, help="Path to the JSON configuration file"
    )

    args = parser.parse_args()

    if not os.path.exists(args.config):
        print(
            f"Error: Configuration file not found at {args.config}",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        with open(args.config, "r", encoding="utf-8") as f:
            params = json.load(f)
    except json.JSONDecodeError:
        print(f"Error: Failed to parse JSON from {args.config}", file=sys.stderr)
        sys.exit(1)

    if "input_path" not in params or not params["input_path"]:
        print(
            "Error: Missing required parameter 'input_path' in JSON file.",
            file=sys.stderr,
        )
        sys.exit(1)

    Config.load_from_dict(params)

    try:
        Config.validate()
    except ValueError as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    try:
        run_assistant(
            input_file_path=params["input_path"],
            custom_instructions=params.get("custom_instructions", ""),
        )

        EmailNotifier.send_notification(
            subject="AI Study Assistant: Processing Completed Successfully",
            body=f"The study guide for '{os.path.basename(params['input_path'])}' has been generated successfully in the /summaries directory.",
        )

    except Exception as e:
        error_message = None
        if hasattr(e, "body") and isinstance(e.body, dict):
            error_message = e.body.get("error", {}).get("message")
        elif hasattr(e, "message"):
            error_message = e.message

        if not error_message:
            error_str = str(e)
            if "'message':" in error_str:
                try:
                    error_message = (
                        error_str.split("'message':")[1]
                        .split("',")[0]
                        .strip(" '\"")
                    )
                except Exception:
                    error_message = error_str
            else:
                error_message = error_str

        EmailNotifier.send_notification(
            subject="AI Study Assistant: Execution Failed",
            body=f"An error occurred during execution:\n\n{error_message}",
        )

        print(f"\n[API Error] Execution failed: {error_message}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()