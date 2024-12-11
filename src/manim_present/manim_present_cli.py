#!/usr/bin/env python3

import os, sys, subprocess, json, argparse, shutil
from PyPDF2 import PdfReader, PdfWriter

def build(python_reqs, html, pdf):
    if not os.path.exists(".venv"):
        print("Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
    
    activate_script = os.path.join(".venv", "bin", "activate")
    if not os.path.exists(activate_script):
        raise FileNotFoundError(f"Activation script not found: {activate_script}")
    os.environ["VIRTUAL_ENV"] = os.path.abspath(".venv")
    os.environ["PATH"] = f"{os.path.abspath('.venv/bin')}:{os.environ.get('PATH', '')}"
    
    if (python_reqs):
        if os.path.exists("./requirements.txt"):
            subprocess.run(["pip", "install", "-r", "requirements.txt"], check=True)
        else:
            print("Installing latest manim-present, add requirements.txt if necessary...")
            subprocess.run(["pip", "install", "-U", "manim-present"], check=True)
    
    print("Running manim-present...")
    subprocess.run(["manim-present"], check=True)
        
    if (html):
        print("Installing npm dependencies...")
        subprocess.run(["npm", "install", "-s", "html-inject-meta"], check=True)
        
        inject_meta_path = "./node_modules/html-inject-meta/cli.js"
        if not os.path.exists(inject_meta_path):
            raise FileNotFoundError(f"`html-inject-meta` CLI not found: {inject_meta_path}")
        
        print("Generating `index.html`...")
        with open("YamlPresentation.html", "r") as input_file, open("index.html", "w") as output_file:
            subprocess.run(["node", inject_meta_path], stdin=input_file, stdout=output_file, check=True)

    if (pdf):
        print("Reading metadata from package.json...")
        with open('package.json', 'r') as f:
            metadata = json.load(f)
        pdf_metadata = {
            '/Title': metadata['html-inject-meta']['name'],
            '/Author': metadata['author'],
            '/Subject': metadata['description'],
            '/Creator': metadata['html-inject-meta']['name'],
            '/Producer': 'Generated with manim-present',
        }
        pdf_path = f'{metadata["name"]}.pdf'

        print(f"Generating {pdf_path} file...")
        subprocess.run(["manim-slides", "convert", "--to", "pdf", "YamlPresentation", pdf_path], check=True)
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.add_metadata(pdf_metadata)
        with open(pdf_path, 'wb') as f:
            writer.write(f)
    
def clean():
    with open('package.json', 'r') as f:
        metadata = json.load(f)
    folders_to_rm = [
        "media",
        "outputs",
        "YamlPresentation_assets",
        "YamlPresentation.html",
        f"{metadata['name']}.pdf",
        "index.html",
        ".venv",
        "slides",
        "node_modules",
        "package-lock.json",
        "package.json",
    ]
    for fol in folders_to_rm:
        if os.path.exists(fol) and os.path.isdir(fol):
            shutil.rmtree(fol)
        if os.path.exists(fol) and not os.path.isdir(fol):
            os.remove(fol)

def main():
    parser = argparse.ArgumentParser(
        description="CLI tool for managing manim-present presentations."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser(
        "build", help="Build the presentation"
    )
    build_parser.add_argument(
        "--python-reqs",
        default=False,
        action="store_true",
        help="Install Python dependencies from requirements.txt into the created virtual env."
    )
    build_parser.add_argument(
        "--html",
        default=True,
        action="store_true",
        help="Generate the `index.html` with HTML metadata injection"
    )
    build_parser.add_argument(
        "--pdf",
        default=True,
        action="store_true",
        help="Generate the PDF file with metadata injection"
    )

    build_parser = subparsers.add_parser(
        "clean", help="Full clean of presentation folder"
    )

    args = parser.parse_args()
    if args.command == "clean":
        clean()
    if args.command == "build":
        build(args.python_reqs, args.html, args.pdf)

if __name__ == "__main__":
    main()
