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


def build_merged_table(primary_file, secondary_file):
    left = clean_columns(read_input_file(primary_file))
    right = clean_columns(read_input_file(secondary_file))

    if "Input date" in left.columns:
        left = left.rename(columns={"Input date": "Entry Date"})

    normalize_datetime_column(left, "Entry Date")
    normalize_datetime_column(right, "Entry Date")

    required_left = ["Patient ID", "Pathway Name", "Content Name", "Entry Date"]
    required_right = ["Patient ID", "Pathway Name", "Content Name", "Entry Date", "Question"]

    require_columns(left, required_left, "Primary input file")
    require_columns(right, required_right, "Secondary input file")

    merge_keys = ["Patient ID", "Pathway Name", "Content Name", "Entry Date"]

    merged = pd.merge(left, right, on=merge_keys, how="left")

    keep_cols = [
        col
        for col in [
            "Patient ID",
            "Pathway Name",
            "Content Name",
            "Scheduled date",
            "Entry Date",
            "Question",
            "Answer Text",
            "Answer Value",
        ]
        if col in merged.columns
    ]

    return merged[keep_cols].copy()


def process_files(primary_file, secondary_file, output_file=None):
    df = build_merged_table(primary_file, secondary_file)

    if "Patient ID" not in df.columns:
        raise ValueError(
            f"'Patient ID' not found after merge. Available columns: {list(df.columns)}"
        )

    df["Answer_Combined"] = pd.NA
    if "Answer Value" in df.columns:
        df["Answer_Combined"] = df["Answer Value"]
    if "Answer Text" in df.columns:
        df["Answer_Combined"] = df["Answer_Combined"].fillna(df["Answer Text"])

    if "Question" not in df.columns:
        raise ValueError(
            f"'Question' not found after merge. Available columns: {list(df.columns)}"
        )

    # First pivot: one row per questionnaire occurrence
    row_id = [
        col for col in
        ["Patient ID", "Pathway Name", "Content Name", "Scheduled date", "Entry Date"]
        if col in df.columns
    ]

    wide_per_event = df.pivot_table(
        index=row_id,
        columns="Question",
        values="Answer_Combined",
        aggfunc="first"
    ).reset_index()

    wide_per_event.columns.name = None

    # Sort events in chronological order
    sort_cols = [col for col in ["Patient ID", "Pathway Name", "Content Name", "Scheduled date", "Entry Date"] if col in wide_per_event.columns]
    if sort_cols:
        wide_per_event = wide_per_event.sort_values(sort_cols).reset_index(drop=True)

    # Create iteration number per repeated questionnaire
    iteration_group = [
        col for col in ["Patient ID", "Pathway Name", "Content Name"] if col in wide_per_event.columns
    ]
    iteration_sort = [col for col in ["Scheduled date", "Entry Date"] if col in wide_per_event.columns]

    if iteration_group and iteration_sort:
        wide_per_event["Iteration"] = (
            wide_per_event
            .sort_values(iteration_group + iteration_sort)
            .groupby(iteration_group)
            .cumcount() + 1
        )
    else:
        raise ValueError("Could not compute iterations because required grouping columns are missing.")

    # Columns to suffix with iteration
    id_cols = [col for col in ["Patient ID", "Pathway Name", "Content Name"] if col in wide_per_event.columns]
    non_value_cols = set(id_cols + ["Scheduled date", "Entry Date", "Iteration"])
    value_cols = [col for col in wide_per_event.columns if col not in non_value_cols]

    # Reshape from event rows to one row per patient/pathway/content
    melted = wide_per_event.melt(
        id_vars=id_cols + ["Iteration"],
        value_vars=value_cols,
        var_name="Question",
        value_name="Value"
    )

    # Remove empty values
    melted = melted.dropna(subset=["Value"])

    # Build final column names like Gewicht_1, Gewicht_2
    melted["Question_Iteration"] = (
        melted["Question"].astype(str).str.strip() + "_" + melted["Iteration"].astype(str)
    )

    final = melted.pivot_table(
        index=id_cols,
        columns="Question_Iteration",
        values="Value",
        aggfunc="first"
    ).reset_index()

    final.columns.name = None

    # Order columns nicely
    base_cols = [col for col in ["Patient ID", "Pathway Name", "Content Name"] if col in final.columns]
    import re

    def sort_question_columns(cols):
        def sort_key(col):
            match = re.match(r"(.*)_(\d+)$", col)
            if match:
                question, num = match.groups()
                return (question, int(num))
            return (col, 0)

        return sorted(cols, key=sort_key)


    base_cols = [col for col in ["Patient ID", "Pathway Name", "Content Name"] if col in final.columns]
    dynamic_cols = [col for col in final.columns if col not in base_cols]

    sorted_dynamic_cols = sort_question_columns(dynamic_cols)

    final = final[base_cols + sorted_dynamic_cols]

    if output_file:
        final.to_csv(output_file, index=False, encoding="utf-8-sig")

    return final