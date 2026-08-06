import base64
import io
import os
import re
import sys
import matplotlib
import markdown
from weasyprint import HTML

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def latex_to_svg_base64(latex_str: str, is_block: bool = False) -> str:
    """Convert a LaTeX string to an SVG image encoded in Base64."""
    latex_str = latex_str.replace(r"\$", "$").replace("$$$", "$$").strip()

    if not latex_str.startswith("$"):
        latex_str = f"${latex_str}$"

    fig = plt.figure(figsize=(0.1, 0.1))
    fontsize = 28 if is_block else 22

    try:
        fig.text(
            0,
            0,
            latex_str,
            fontsize=fontsize,
            usetex=False,
            math_fontfamily="cm",
        )

        buffer = io.BytesIO()
        plt.savefig(
            buffer, format="svg", bbox_inches="tight", pad_inches=0.05, transparent=True
        )
        plt.close(fig)

        buffer.seek(0)
        svg_code = buffer.read().decode("utf-8")
        b64_svg = base64.b64encode(svg_code.encode("utf-8")).decode("utf-8")
        return f"data:image/svg+xml;base64,{b64_svg}"
    except Exception:
        plt.close(fig)
        return None


def render_math_to_svg_html(md_text: str) -> str:
    def replace_block(match):
        formula = match.group(1).strip()
        img_data = latex_to_svg_base64(formula, is_block=True)
        if img_data:
            return f'<div class="math-block"><img src="{img_data}" alt="{formula}" /></div>'
        return f"$${formula}$$"

    def replace_inline(match):
        formula = match.group(1).strip()
        img_data = latex_to_svg_base64(formula, is_block=False)
        if img_data:
            return f'<img class="math-inline" src="{img_data}" alt="{formula}" />'
        return f"${formula}$"

    md_text = re.sub(r"\$\$\s*(.*?)\s*\$\$", replace_block, md_text, flags=re.DOTALL)
    md_text = re.sub(r"(?<!\$)\$([^\$\n]+?)\$(?!\$)", replace_inline, md_text)

    return md_text


def convert_md_to_pdf(input_md_path: str, output_pdf_path: str = None) -> str:
    """Read a markdown file, render its equations to SVG, and generate a PDF."""
    if not os.path.exists(input_md_path):
        raise FileNotFoundError(f"El archivo '{input_md_path}' no existe.")

    if output_pdf_path is None:
        base_name = os.path.splitext(input_md_path)[0]
        output_pdf_path = f"{base_name}.pdf"

    with open(input_md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    processed_md = render_math_to_svg_html(md_text)

    html_content = markdown.markdown(
        processed_md, extensions=["tables", "fenced_code", "toc"]
    )

    full_html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Guía de Estudio</title>
        <style>
            @page {{
                size: A4;
                margin: 2.5cm;
                @bottom-right {{
                    content: counter(page);
                    font-family: Arial, sans-serif;
                    font-size: 9pt;
                    color: #666;
                }}
            }}
            body {{
                font-family: 'Helvetica Neue', Arial, sans-serif;
                font-size: 11pt;
                line-height: 1.8;
                color: #2b2b2b;
            }}
            h1 {{
                color: #1a365d;
                font-size: 18pt;
                border-bottom: 2px solid #2b6cb0;
                padding-bottom: 6px;
                margin-top: 0;
            }}
            h2 {{
                color: #2b6cb0;
                font-size: 14pt;
                margin-top: 20px;
                border-bottom: 1px solid #e2e8f0;
                padding-bottom: 4px;
            }}
            h3 {{
                color: #2d3748;
                font-size: 12pt;
                margin-top: 15px;
            }}
            p {{
                margin-bottom: 12px;
                text-align: justify;
            }}
            .math-block {{
                display: block;
                text-align: center;
                margin: 1.8em 0;
            }}
            .math-block img {{
                max-width: 95%;
                height: auto;
                transform: scale(1.45); 
            }}
            .math-inline {{
                vertical-align: -0.4em;
                height: 2.1em; 
                margin: 0 4px;
            }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """

    print(f" -> [PDF Exporter] File PDF generated at: {output_pdf_path}...")
    HTML(string=full_html).write_pdf(output_pdf_path)
    print(" -> [PDF Exporter] ¡PDF generated with success!")
    return output_pdf_path