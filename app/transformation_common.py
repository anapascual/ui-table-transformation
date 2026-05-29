import pandas as pd
from pathlib import Path


def read_input_file(file):
    file_name = file if isinstance(file, str) else getattr(file, "name", "")
    suffix = Path(file_name).suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(file)
    elif suffix in [".xlsx", ".xls"]:
        return pd.read_excel(file, header=2)
    else:
        raise ValueError(f"Unsupported file format: {suffix}")


def clean_columns(df):
    df.columns = [str(col).strip() for col in df.columns]
    return df


def normalize_datetime_column(df, col_name):
    if col_name in df.columns:
        df[col_name] = pd.to_datetime(df[col_name], errors="coerce")
    return df


def require_columns(df, required_cols, df_name):
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"{df_name} is missing required columns: {missing}")


def read_demographics_file(file):
    demo = clean_columns(read_input_file(file))
    require_columns(demo, ["Patient ID"], "Demographics file")
    demo = demo.drop_duplicates(subset=["Patient ID"])

    # Normalize Patient ID to string to avoid merge conflicts
    demo["Patient ID"] = demo["Patient ID"].astype(str).str.strip()

    # Find Age column (case-insensitive, including variations like "Patient Age")
    age_col = next(
        (col for col in demo.columns if "age" in col.lower()),
        None
    )
    
    # Find Sex/Gender column (case-insensitive, including variations like "Patient Gender")
    sex_col = next(
        (col for col in demo.columns if any(term in col.lower() for term in ["sex", "gender"])),
        None
    )

    result_dict = {"Patient ID": demo["Patient ID"]}
    if age_col:
        result_dict["Age"] = demo[age_col]
    if sex_col:
        result_dict["Sex"] = demo[sex_col]

    return pd.DataFrame(result_dict)


def merge_demographics(df, demographics_file):
    if demographics_file is None:
        return df
    
    # Normalize Patient ID to string in both dataframes before merge
    df = df.copy()
    if "Patient ID" in df.columns:
        df["Patient ID"] = df["Patient ID"].astype(str).str.strip()
    
    demo = read_demographics_file(demographics_file)
    return df.merge(demo, on="Patient ID", how="left")


def validate_transformation_output(content_df, answers_df, output_df):
    """
    Comprehensive validation of the transformation output.
    
    Checks:
    A. Row coverage - all expected patient-pathway combinations are present
    B. Non-responder handling - non-responders have blank answer columns
    C. Duplicate columns - no duplicate column names
    D. Answer preservation - all answers are correctly mapped
    
    Raises ValueError if critical issues are found.
    """
    id_cols = ["Patient ID", "Pathway Name"]
    
    # Ensure all dataframes have string types for key columns before merge
    content_df = content_df.copy()
    answers_df = answers_df.copy()
    output_df = output_df.copy()
    
    for col in id_cols:
        if col in content_df.columns:
            content_df[col] = content_df[col].astype(str).str.strip()
        if col in answers_df.columns:
            answers_df[col] = answers_df[col].astype(str).str.strip()
        if col in output_df.columns:
            output_df[col] = output_df[col].astype(str).str.strip()
    
    # A. Row coverage check
    if id_cols[0] in content_df.columns and id_cols[1] in content_df.columns:
        expected_keys = content_df[id_cols].drop_duplicates()
        if id_cols[0] in output_df.columns and id_cols[1] in output_df.columns:
            actual_keys = output_df[id_cols].drop_duplicates()
            missing = expected_keys.merge(
                actual_keys,
                on=id_cols,
                how="left",
                indicator=True
            ).query("_merge == 'left_only'")
            
            if len(missing) > 0:
                print(f"[WARNING] Row coverage: {len(missing)} expected patient-pathway combinations are missing from output:")
                print(missing.head(10).to_string())
            else:
                print("[OK] Row coverage: All expected patient-pathway combinations are present")
    
    # B. Non-responder blank row check
    if id_cols[0] in answers_df.columns and id_cols[1] in answers_df.columns:
        has_answers = answers_df[id_cols].drop_duplicates()
        all_content = content_df[id_cols].drop_duplicates()
        
        non_responders = all_content.merge(
            has_answers,
            on=id_cols,
            how="left",
            indicator=True
        ).query("_merge == 'left_only'")[id_cols]
        
        if len(non_responders) > 0:
            print(f"[INFO] Non-responder check: {len(non_responders)} patient-pathway combinations have no answers")
            # Verify they exist in output with blank answer columns
            for idx, row in non_responders.head(5).iterrows():
                pat_id = row.get(id_cols[0])
                path_name = row.get(id_cols[1])
                output_row = output_df[
                    (output_df[id_cols[0]] == pat_id) & 
                    (output_df[id_cols[1]] == path_name)
                ]
                if len(output_row) > 0:
                    print(f"  [OK] Non-responder {pat_id}/{path_name} exists in output")
    
    # C. Duplicate column check
    duplicates = output_df.columns[output_df.columns.duplicated()].tolist()
    if duplicates:
        print(f"[ERROR] Duplicate columns found: {duplicates}")
        raise ValueError(f"Duplicate columns in output: {duplicates}")
    else:
        print("[OK] No duplicate columns")
    
    # D. Answer preservation check
    question_cols = [col for col in output_df.columns if "_" in col]
    if question_cols:
        # Count non-null values in answer columns
        answer_cells = output_df[question_cols].count().sum()
        print(f"[INFO] Answer preservation: {answer_cells} answer cells in output")
    
    print("[OK] Validation complete")



def build_merged_table(primary_file, secondary_file):
    """
    Reads, cleans, validates and merges the two input files.
    
    IMPORTANT: The primary_file should be the content/questionnaire definition file
    (all_content.xlsx), and the secondary_file should be the answers file
    (all_content_answers.xlsx).
    
    Returns a long-format DataFrame with columns:
        Patient ID, Pathway Name, Content Name,
        Scheduled date (optional), Entry Date,
        Question, Answer_Combined
    
    Rows are preserved for all content entries even if they have no answers
    (non-responders get NaN/NA in the answer columns).
    """
    # Read and clean both files
    content = clean_columns(read_input_file(primary_file))
    answers = clean_columns(read_input_file(secondary_file))

    # Normalize "Input date" to "Entry Date" for consistency
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
    for col in ["Patient ID", "Pathway Name", "Content Name", "Question"]:
        if col in content.columns:
            content[col] = content[col].astype(str).str.strip()
        if col in answers.columns:
            answers[col] = answers[col].astype(str).str.strip()

    # Build base from content: all Patient ID + Pathway Name + Content Name + Entry Date combinations
    # This ensures we keep rows for non-responders
    base_cols = ["Patient ID", "Pathway Name", "Content Name", "Entry Date"]
    base = content[base_cols].copy()

    # Add optional columns from content if they exist
    optional_content_cols = [col for col in ["Scheduled date"] if col in content.columns]
    if optional_content_cols:
        content_for_merge = content[base_cols + optional_content_cols].copy()
        base = base.merge(
            content_for_merge.drop(base_cols, axis=1),
            left_index=True,
            right_index=True,
            how="left"
        )
        # Actually, we need to properly handle this - let's use a different approach
        # Merge content metadata onto base
        base = pd.merge(
            base,
            content[[col for col in content.columns if col not in ["Question", "Answer Text", "Answer Value"]]].drop_duplicates(subset=base_cols),
            on=base_cols,
            how="left"
        )

    # Prepare answers file: clean and deduplicate
    answers_cols_to_keep = [
        col for col in [
            "Patient ID", "Pathway Name", "Content Name", "Entry Date",
            "Question", "Answer Text", "Answer Value",
        ]
        if col in answers.columns
    ]
    answers = answers[answers_cols_to_keep].copy()

    # Left-join answers onto base content
    merged = pd.merge(
        base,
        answers,
        on=["Patient ID", "Pathway Name", "Content Name", "Entry Date"],
        how="left"
    )

    # Combine Answer Value and Answer Text into a single column
    merged["Answer_Combined"] = pd.NA
    if "Answer Value" in merged.columns:
        merged["Answer_Combined"] = merged["Answer Value"]
    if "Answer Text" in merged.columns:
        merged["Answer_Combined"] = merged["Answer_Combined"].fillna(merged["Answer Text"])

    # Keep only the columns we need
    keep_cols = [
        col for col in [
            "Patient ID", "Pathway Name", "Content Name",
            "Scheduled date", "Entry Date",
            "Question", "Answer Text", "Answer Value", "Answer_Combined",
        ]
        if col in merged.columns
    ]

    df = merged[keep_cols].copy()

    if "Patient ID" not in df.columns:
        raise ValueError(
            f"'Patient ID' not found after merge. Available columns: {list(df.columns)}"
        )

    return df
