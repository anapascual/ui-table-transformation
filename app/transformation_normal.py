import pandas as pd
from transformation_common import (
    merge_demographics, 
    read_input_file,
    clean_columns,
    normalize_datetime_column,
    require_columns,
    validate_transformation_output,
)


def process_normal_files(primary_file, secondary_file, demographics_file=None, output_file=None):
    """
    Normal (non-iterative) questionnaire workflow.

    Each patient/pathway/content appears only ONCE in the input data.
    Output: one row per questionnaire event, with Scheduled date and
    Entry Date included, and one column per question.

    Rows where Scheduled date is missing are preserved — NaT/NaN is a
    valid state (patient answered but was not formally scheduled).
    
    Non-responders (patients with scheduled content but no answers) are
    also preserved as rows with blank answer columns.
    """
    print("\n[INFO] Starting normal transformation...")
    
    # Read and clean files
    content = clean_columns(read_input_file(primary_file))
    answers = clean_columns(read_input_file(secondary_file))
    
    # Rename "Input date" to "Entry Date" for consistency
    if "Input date" in content.columns:
        content = content.rename(columns={"Input date": "Entry Date"})
    if "Input date" in answers.columns:
        answers = answers.rename(columns={"Input date": "Entry Date"})
    
    # Normalize datetime columns
    normalize_datetime_column(content, "Entry Date")
    normalize_datetime_column(answers, "Entry Date")
    normalize_datetime_column(content, "Scheduled date")
    normalize_datetime_column(answers, "Scheduled date")
    
    # Validate required columns
    required_content = ["Patient ID", "Pathway Name", "Content Name", "Entry Date"]
    required_answers = ["Patient ID", "Pathway Name", "Content Name", "Entry Date", "Question"]
    require_columns(content, required_content, "Content/Primary input file")
    require_columns(answers, required_answers, "Answers/Secondary input file")
    
    # Normalize all key columns to string type to avoid merge conflicts
    # (CSV reads as str, Excel may read as int, etc.)
    for col in ["Patient ID", "Pathway Name", "Content Name"]:
        content[col] = content[col].astype(str).str.strip()
        answers[col] = answers[col].astype(str).str.strip()
    
    if "Question" in answers.columns:
        answers["Question"] = answers["Question"].astype(str).str.strip()
    
    print(f"[INFO] Content file: {content.shape[0]} rows")
    print(f"[INFO] Answers file: {answers.shape[0]} rows")
    
    # Build base from content (all expected patient-pathway-content combinations)
    id_cols = [col for col in ["Patient ID", "Pathway Name", "Content Name"] if col in content.columns]
    date_cols = [col for col in ["Scheduled date", "Entry Date"] if col in content.columns]
    
    base = content[id_cols + date_cols].copy()
    base = base.drop_duplicates()
    
    # Merge demographics if provided
    if demographics_file:
        base = merge_demographics(base, demographics_file)
    
    print(f"[INFO] Base rows (unique patient-pathway-content combinations): {len(base)}")
    
    # Prepare answers: keep only rows with actual questions and answers
    answers_keep = answers[[col for col in id_cols + date_cols + ["Question", "Answer Text", "Answer Value"] if col in answers.columns]].copy()
    
    # Combine Answer Value and Answer Text
    answers_keep["Answer_Combined"] = pd.NA
    if "Answer Value" in answers_keep.columns:
        answers_keep["Answer_Combined"] = answers_keep["Answer Value"]
    if "Answer Text" in answers_keep.columns:
        answers_keep["Answer_Combined"] = answers_keep["Answer_Combined"].fillna(answers_keep["Answer Text"])
    
    # Pivot answers to wide format
    SENTINEL_DATE = pd.Timestamp("1900-01-01")
    SENTINEL_STR = "___MISSING___"
    
    # Replace NaN/NaT in date columns with sentinels to preserve rows during pivot
    for col in date_cols:
        if pd.api.types.is_datetime64_any_dtype(answers_keep[col]):
            answers_keep[col] = answers_keep[col].fillna(SENTINEL_DATE)
        else:
            answers_keep[col] = answers_keep[col].fillna(SENTINEL_STR)
    
    answers_wide = answers_keep.pivot_table(
        index=id_cols + date_cols,
        columns="Question",
        values="Answer_Combined",
        aggfunc="first",
    ).reset_index()
    answers_wide.columns.name = None
    
    # Restore sentinels back to NaN/NaT
    for col in date_cols:
        if pd.api.types.is_datetime64_any_dtype(answers_wide[col]):
            answers_wide[col] = answers_wide[col].replace(SENTINEL_DATE, pd.NaT)
        else:
            answers_wide[col] = answers_wide[col].replace(SENTINEL_STR, pd.NA)
    
    # Left join answers onto base (preserves non-responders)
    final = pd.merge(base, answers_wide, on=id_cols + date_cols, how="left")
    
    print(f"[INFO] Final output rows: {final.shape[0]}")
    print(f"[INFO] Final output columns: {final.shape[1]}")
    
    # Reorder columns: base IDs, demographics, dates, then questions
    base_cols = [col for col in id_cols if col in final.columns]
    demo_cols = [col for col in ["Age", "Sex", "Gender"] if col in final.columns]
    remaining_date_cols = [col for col in date_cols if col in final.columns]
    question_cols = [col for col in final.columns if col not in base_cols + demo_cols + remaining_date_cols]
    
    final = final[base_cols + demo_cols + remaining_date_cols + question_cols]
    
    # Validation checks
    print("\n[INFO] Running validation checks...")
    try:
        validate_transformation_output(content, answers, final)
    except ValueError as e:
        print(f"[ERROR] Validation failed: {e}")
        raise
    
    if output_file:
        final.to_csv(output_file, index=False, encoding="utf-8-sig")
        print(f"\n[INFO] Output saved to: {output_file}")
    
    print(f"[INFO] Transformation complete!\n")
    
    return final
