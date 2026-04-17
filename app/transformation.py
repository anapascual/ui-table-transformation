import pandas as pd
from pathlib import Path


def read_input_file(file):
    file_name = file if isinstance(file, str) else getattr(file, "name", "")
    suffix = Path(file_name).suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(file)
    elif suffix in [".xlsx", ".xls"]:
        # your Excel file has headers starting on row 3
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


def build_merged_table(schedule_file, answers_file):
    schedule = clean_columns(read_input_file(schedule_file))
    answers = clean_columns(read_input_file(answers_file))

    if "Input date" in schedule.columns:
        schedule = schedule.rename(columns={"Input date": "Entry Date"})

    schedule = normalize_datetime_column(schedule, "Entry Date")
    answers = normalize_datetime_column(answers, "Entry Date")

    merge_keys = ["Patient ID", "Pathway Name", "Content Name", "Entry Date"]

    merged = pd.merge(schedule, answers, on=merge_keys, how="left")

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

    merged = merged[keep_cols].copy()
    return merged


def process_files(schedule_file, answers_file, output_file=None):
    df = build_merged_table(schedule_file, answers_file)

    df["Answer_Combined"] = pd.NA
    if "Answer Value" in df.columns:
        df["Answer_Combined"] = df["Answer Value"]
    if "Answer Text" in df.columns:
        df["Answer_Combined"] = df["Answer_Combined"].fillna(df["Answer Text"])

    id_columns = [
        col
        for col in ["Patient ID", "Pathway Name", "Content Name", "Scheduled date", "Entry Date"]
        if col in df.columns
    ]

    final = df.pivot_table(
        index=id_columns,
        columns="Question",
        values="Answer_Combined",
        aggfunc="first"
    ).reset_index()

    final.columns.name = None

    sort_cols = [col for col in ["Patient ID", "Scheduled date", "Entry Date"] if col in final.columns]
    if sort_cols:
        final = final.sort_values(sort_cols).reset_index(drop=True)

    final = final.where(pd.notna(final), "")

    if output_file:
        final.to_csv(output_file, index=False, encoding="utf-8-sig")

    return final