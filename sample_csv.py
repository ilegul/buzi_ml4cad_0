import pandas as pd
import csv
from pathlib import Path

# Percorso input (WSL)
input_path = "/home/ileniag/buzi_ml4cad_0/data/raw/data_cvd.csv"
output_path = Path("/home/ileniag/buzi_ml4cad_0/campioni_random.csv")

# --- Rileva separatore e header con csv.Sniffer ---
with open(input_path, "r", encoding="utf-8", errors="replace") as f:
    sample_text = f.read(1024 * 1024)  # fino a ~1MB per sniffing

# Prova a sniffare; in caso di fallimento usa fallback ","
try:
    dialect = csv.Sniffer().sniff(sample_text, delimiters=[",", ";", "\t", "|"])
    sep = dialect.delimiter
    has_header = csv.Sniffer().has_header(sample_text)
except Exception:
    sep = ","
    has_header = True

header_arg = 0 if has_header else None

# --- Leggi il CSV saltando righe problematiche ---
df = pd.read_csv(
    input_path,
    sep=sep,
    engine="python",          # più tollerante
    quotechar='"',            # gestisce campi con separatore tra virgolette
    doublequote=True,
    escapechar="\\",
    on_bad_lines="skip",      # <— salta righe malformate
    header=header_arg
)

# Se il file ha meno di 10 righe valide, prende tutte
n_samples = min(10, len(df))
sample = df.sample(n=n_samples, random_state=None)

# Salva il risultato
sample.to_csv(output_path, index=False)
print(f"Rilevato separatore: {repr(sep)} | Header: {has_header}")
print(f"Righe lette: {len(df)} | Campioni salvati: {n_samples}")
print(f"File scritto in: {output_path}")
