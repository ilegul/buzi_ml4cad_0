import pandas as pd
import csv
from pathlib import Path

# ======= Config minima: percorso del file =======
CSV_PATH = "/home/ileniag/buzi_ml4cad_0/data/raw/data_cvd.csv"  # cambia se vuoi
YEARS_THRESHOLD = 7
# =================================================

# Colonne rilevate nel tuo file campione
ID_COL = "Number"
DRAW_DATE_COL = "Data prelievo"
FOLLOWUP_DATE_COL = "Follow Up Data"
DEATH_DATE_COL = "Data of death"
CVD_FLAG_COL = "CVD Death"          # 0/1
CAUSE_TEXT_COL = "Cause of death"    # testo (es. Stroke, Other cardiac causes)

# Eventuali flag non-CVD presenti (0/1) — aggiungi qui se nel file completo ce ne sono altri
NONCVD_FLAG_COLS = ["Accident", "Suicide", "UnKnown"]

# Dizionari/insiemi di mapping
TRUE_SET = {"1", 1, True, "true", "yes", "s", "si", "sì"}
FALSE_SET = {"0", 0, False, "false", "no", "n"}

# Valori testuali da considerare CVD nella colonna "Cause of death"
CVD_TEXT_SET = {
    "cvd", "cardiovascular", "cardiac", "other cardiac causes",
    "stroke", "myocardial infarction", "fatal mi", "sudden death",
    "ischemic", "heart failure"
}

def smart_read_csv(path: str) -> pd.DataFrame:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        sample = f.read(1024 * 1024)
    try:
        sep = csv.Sniffer().sniff(sample, delimiters=[",",";","\t","|"]).delimiter
    except Exception:
        sep = ","
    return pd.read_csv(path, sep=sep, engine="python", on_bad_lines="skip", dtype=str)

def as_bool_series(s: pd.Series) -> pd.Series:
    if s is None:
        return pd.Series([False] * 0)
    x = s.fillna("").astype(str).str.strip().str.lower()
    return x.isin({str(v).lower() for v in TRUE_SET})

def main():
    path = Path(CSV_PATH)
    if not path.exists():
        raise FileNotFoundError(f"CSV non trovato: {path}")

    df = smart_read_csv(str(path))
    cols = {c.lower(): c for c in df.columns}

    def need(name):
        key = name.lower()
        if key not in cols:
            raise KeyError(f"Colonna non trovata nel CSV: {name}")
        return cols[key]

    # Allinea ai nomi effettivi (case-insensitive)
    id_col = need(ID_COL)
    draw_col = need(DRAW_DATE_COL)
    fu_col = need(FOLLOWUP_DATE_COL)
    death_col = need(DEATH_DATE_COL)
    cvd_flag_col = need(CVD_FLAG_COL)
    cause_text_col = need(CAUSE_TEXT_COL)

    noncvd_cols = [cols[c.lower()] for c in NONCVD_FLAG_COLS if c.lower() in cols]

    # Parse date (ISO nel campione; se avessi gg/mm/aaaa, imposta dayfirst=True)
    draw_dt = pd.to_datetime(df[draw_col], errors="coerce", dayfirst=False)
    fu_dt = pd.to_datetime(df[fu_col], errors="coerce", dayfirst=False)
    death_dt = pd.to_datetime(df[death_col], errors="coerce", dayfirst=False)

    # Durata follow-up - prelievo in anni
    duration_years = (fu_dt - draw_dt).dt.days / 365.25
    valid_duration = duration_years.notna()
    within = valid_duration & (duration_years <= YEARS_THRESHOLD)
    beyond = valid_duration & (duration_years > YEARS_THRESHOLD)

    # Flag CVD da colonna 0/1
    cvd_flag = as_bool_series(df[cvd_flag_col])

    # CVD anche da testo (fallback)
    cause_txt = df[cause_text_col].fillna("").str.strip().str.lower()
    cvd_text = cause_txt.apply(
        lambda x: any(tok in x for tok in CVD_TEXT_SET) if x else False
    )

    is_cvd_death = cvd_flag | cvd_text

    # Flag NON-CVD: qualsiasi colonna binaria non-CVD = 1
    noncvd_any = None
    if noncvd_cols:
        noncvd_bools = [as_bool_series(df[c]) for c in noncvd_cols]
        # riallinea lunghezza
        noncvd_bools = [s.reindex(df.index, fill_value=False) for s in noncvd_bools]
        noncvd_any = noncvd_bools[0]
        for s in noncvd_bools[1:]:
            noncvd_any = noncvd_any | s
    else:
        noncvd_any = pd.Series([False] * len(df), index=df.index)

    # Consideriamo "deceduto" chi ha data di decesso oppure CVD/nonCVD flag
    has_death_date = death_dt.notna()
    is_dead = has_death_date | is_cvd_death | noncvd_any

    # Se ha data di decesso ma non è CVD secondo i flag/testo -> NON-CVD
    is_noncvd_death = (~is_cvd_death) & (noncvd_any | has_death_date)

    # Vivi = non deceduti
    is_alive = ~is_dead

    # Conteggi
    n_patients = df[id_col].nunique()

    n_alive = int(is_alive.sum())
    n_dead_cvd = int(is_cvd_death.sum())
    n_dead_cvd_within = int((is_cvd_death & within).sum())
    n_dead_cvd_beyond = int((is_cvd_death & beyond).sum())

    n_dead_noncvd = int(is_noncvd_death.sum())
    n_dead_noncvd_within = int((is_noncvd_death & within).sum())
    n_dead_noncvd_beyond = int((is_noncvd_death & beyond).sum())

    print("=== Report conteggi ===")
    print(f"1) Pazienti totali: {n_patients}")
    print(f"2) Vivi: {n_alive}")
    print(f"3) Morti CVD: {n_dead_cvd}")
    print(f"4) Morti CVD entro {YEARS_THRESHOLD} anni: {n_dead_cvd_within}")
    print(f"5) Morti CVD oltre {YEARS_THRESHOLD} anni: {n_dead_cvd_beyond}")
    print(f"6) Morti non CVD: {n_dead_noncvd}")
    print(f"7) Morti non CVD entro {YEARS_THRESHOLD} anni: {n_dead_noncvd_within}")
    print(f"8) Morti non CVD oltre {YEARS_THRESHOLD} anni: {n_dead_noncvd_beyond}")

    # (opzionale) salva un audit per verifiche
    audit = pd.DataFrame({
        ID_COL: df[id_col],
        "duration_years": duration_years,
        "is_alive": is_alive.astype(int),
        "is_dead": is_dead.astype(int),
        "is_cvd_death": is_cvd_death.astype(int),
        "is_noncvd_death": is_noncvd_death.astype(int),
        f"entro_{YEARS_THRESHOLD}y": within.astype(int),
        f"oltre_{YEARS_THRESHOLD}y": beyond.astype(int),
        "cause_text": df[cause_text_col],
        "cvd_flag": df[cvd_flag_col],
    })
    out_csv = Path(CSV_PATH).with_name("audit_conteggi.csv")
    audit.to_csv(out_csv, index=False)
    print(f"\nDettaglio per audit salvato in: {out_csv}")

if __name__ == "__main__":
    main()
