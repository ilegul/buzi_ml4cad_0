import os
from pathlib import Path
import html2text

def convert_html_to_markdown(input_folder="exported_notebooks"):
    """
    Converte tutti i file HTML nella cartella specificata in Markdown
    
    Args:
        input_folder: nome della sottocartella con i file HTML
    """
    # Ottieni il percorso della cartella dello script
    script_dir = Path(__file__).parent
    html_folder = script_dir / input_folder
    
    # Verifica che la cartella esista
    if not html_folder.exists():
        print(f"Errore: La cartella '{input_folder}' non esiste!")
        return
    
    # Configura html2text
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.ignore_emphasis = False
    h.body_width = 0  # Non limitare la larghezza delle righe
    
    # Trova tutti i file HTML
    html_files = list(html_folder.glob("*.html"))
    
    if not html_files:
        print(f"Nessun file HTML trovato in '{input_folder}'")
        return
    
    print(f"Trovati {len(html_files)} file HTML da convertire...\n")
    
    # Converti ogni file
    for html_file in html_files:
        try:
            # Leggi il contenuto HTML
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Converti in Markdown
            markdown_content = h.handle(html_content)
            
            # Crea il nome del file di output
            md_file = html_file.with_suffix('.md')
            
            # Salva il file Markdown
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            print(f"✓ Convertito: {html_file.name} → {md_file.name}")
            
        except Exception as e:
            print(f"✗ Errore con {html_file.name}: {str(e)}")
    
    print(f"\nConversione completata!")

if __name__ == "__main__":
    convert_html_to_markdown()