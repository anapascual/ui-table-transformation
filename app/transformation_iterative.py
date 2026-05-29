import pandas as pd
from transformation_common import (
    merge_demographics,
    read_input_file,
    clean_columns,
    normalize_datetime_column,
    require_columns,
    validate_transformation_output,
)

ITERATIVE_CONTENT_NAME_KEYWORDS = [
    "Allgemeine Gesundheit",
    "Schmerztagebuch",
    "Tagesbericht zuhause",
    "BMI",
]


def sort_question_columns(cols):
    """
    Sort columns by base name then by numeric iteration suffix.
    Columns named {ContentName}_{Question}_{N} are grouped by their
    base (everything before the trailing _N) then ordered by N.
    """
    def parse_column(col):
        col = str(col).strip()
        parts = col.rsplit("_", maxsplit=1)
        if len(parts) == 2 and parts[1].isdigit():
            return (parts[0], int(parts[1]))
        return (col, 0)

    return sorted(cols, key=parse_column)


def process_iterative_files(primary_file, secondary_file, demographics_file=None, output_file=None):
    """
    Iterative questionnaire workflow.

    Output: one row per unique Patient ID + Pathway Name from the content
    file.  Repeated answers for the same question are placed in separate
    columns suffixed _1, _2, _3 … ordered chronologically by Entry Date.

    Column naming: {Content Name}_{Question}_{iteration_number}

    Non-responders (patients in the content file with no answers) are
    preserved as rows with blank answer columns.
    """
    print("\n[INFO] Starting iterative transformation...")

    # ── Step 1: Read and clean files ──────────────────────────────────────
    content = clean_columns(read_input_file(primary_file))
    answers = clean_columns(read_input_file(secondary_file))

    if "Input date" in content.columns:
        content = content.rename(columns={"Input date": "Entry Date"})
    if "Input date" in answers.columns:
        answers = answers.rename(columns={"Input date": "Entry Date"})

    normalize_datetime_column(content, "Entry Date")
    normalize_datetime_column(answers, "Entry Date")
    normalize_datetime_column(content, "Scheduled date")
    normalize_datetime_column(answers, "Scheduled date")

    require_columns(content, ["Patient ID", "Pathway Name"], "Content/Primary input file")
    require_columns(answers, ["Patient ID", "Pathway Name", "Content Name", "Question"],
                    "Answers/Secondary input file")

    for col in ["Patient ID", "Pathway Name", "Content Name", "Question"]:
        if col in content.columns:
            content[col] = content[col].astype(str).str.strip()
        if col in answers.columns:
            answers[col] = answers[col].astype(str).str.strip()

    print(f"[INFO] Content file: {content.shape[0]} rows")
    print(f"[INFO] Answers file: {answers.shape[0]} rows")

    # ── Step 2: Build base from content (unique Patient ID + Pathway Name) ─
    id_cols = ["Patient ID", "Pathway Name"]
    base = content[id_cols].drop_duplicates().copy()

    if demographics_file:
        base = merge_demographics(base, demographics_file)

    print(f"[INFO] Base rows (unique patient-pathway combinations): {len(base)}")

    # ── Step 3: Prepare answers ────────────────────────────────────────────
    answers_clean = answers.dropna(
        subset=["Patient ID", "Pathway Name", "Content Name", "Question"], how="any"
    ).copy()

    # Normalise Content Name and Question: strip + collapse internal whitespace
    for col in ["Content Name", "Question"]:
        answers_clean[col] = (
            answers_clean[col]
            .astype(str)
            .str.strip()
            .str.replace(r"\s+", " ", regex=True)
        )

    # Combine Answer Value and Answer Text into a single column
    answers_clean["Answer_Combined"] = pd.NA
    if "Answer Value" in answers_clean.columns:
        answers_clean["Answer_Combined"] = answers_clean["Answer Value"]
    if "Answer Text" in answers_clean.columns:
        answers_clean["Answer_Combined"] = answers_clean["Answer_Combined"].fillna(
            answers_clean["Answer Text"]
        )

    # ── Step 4: Sort by Entry Date and assign iteration numbers ───────────
    sort_key = ["Patient ID", "Pathway Name", "Content Name", "Question"]
    if "Entry Date" in answers_clean.columns:
        answers_clean = (
            answers_clean
            .sort_values(sort_key + ["Entry Date"], na_position="last")
            .reset_index(drop=True)
        )

    answers_clean["iteration"] = (
        answers_clean
        .groupby(["Patient ID", "Pathway Name", "Content Name", "Question"])
        .cumcount()
        .add(1)
    )

    # ── Step 5: Build stable column names: {Content Name}_{Question}_{N} ──
    answers_clean["question_column"] = (
        answers_clean["Content Name"].astype(str).str.strip()
        + "_"
        + answers_clean["Question"].astype(str).str.strip()
        + "_"
        + answers_clean["iteration"].astype(str)
    )

    print(f"[INFO] Unique question columns: {answers_clean['question_column'].nunique()}")

    # ── Step 6: Pivot answers to wide format ──────────────────────────────
    answers_wide = answers_clean.pivot_table(
        index=["Patient ID", "Pathway Name"],
        columns="question_column",
        values="Answer_Combined",
        aggfunc="first",
    ).reset_index()
    answers_wide.columns.name = None

    print(f"[INFO] Answer columns created: {len(answers_wide.columns) - len(id_cols)}")

    # ── Step 7: Left join onto base (preserves non-responders) ───────────
    final = pd.merge(base, answers_wide, on=id_cols, how="left")

    print(f"[INFO] Final output rows: {final.shape[0]}")
    print(f"[INFO] Final output columns: {final.shape[1]}")

    # ── Step 8: Order columns ─────────────────────────────────────────────
    base_id_cols = [col for col in id_cols if col in final.columns]
    demo_cols = [col for col in ["Age", "Sex", "Gender"] if col in final.columns]
    dynamic_cols = [col for col in final.columns if col not in base_id_cols + demo_cols]

    final = final[base_id_cols + demo_cols + sort_question_columns(dynamic_cols)]

    # ── Step 9: Validation ────────────────────────────────────────────────
    print("\n[INFO] Running validation checks...")
    try:
        validate_transformation_output(content, answers_clean, final)
    except ValueError as e:
        print(f"[ERROR] Validation failed: {e}")
        raise

    duplicates = final.columns[final.columns.duplicated()].tolist()
    if duplicates:
        raise ValueError(f"Duplicate columns detected: {duplicates}")

    # ── Step 10: Export ───────────────────────────────────────────────────
    if output_file:
        final.to_csv(output_file, index=False, encoding="utf-8-sig")
        print(f"\n[INFO] Output saved to: {output_file}")

    print(f"[INFO] Transformation complete!\n")

    return final
