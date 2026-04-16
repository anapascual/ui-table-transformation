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


def combine_value_columns(df, value_priority, output_column="Value_Combined"):
    df[output_column] = pd.NA

    for col in value_priority:
        if col in df.columns:
            if df[output_column].isna().all():
                df[output_column] = df[col]
            else:
                df[output_column] = df[output_column].fillna(df[col])

    return df


def process_files_generic(left_file, right_file, config, output_file=None):
    left_df = read_input_file(left_file)
    right_df = read_input_file(right_file)

    if config.get("rename_left"):
        left_df = left_df.rename(columns=config["rename_left"])

    if config.get("rename_right"):
        right_df = right_df.rename(columns=config["rename_right"])

    merge_on = config["merge_on"]

    for col in merge_on:
        if col in left_df.columns:
            left_df[col] = pd.to_datetime(left_df[col], errors="ignore")
        if col in right_df.columns:
            right_df[col] = pd.to_datetime(right_df[col], errors="ignore")

    merged = pd.merge(left_df, right_df, on=merge_on, how="left")

    selected_cols = config.get("selected_columns_after_merge")
    if selected_cols:
        merged = merged[selected_cols].copy()

    rename_after_merge = config.get("rename_after_merge")
    if rename_after_merge:
        merged = merged.rename(columns=rename_after_merge)

    merged = combine_value_columns(
        merged,
        value_priority=config["value_priority"],
        output_column="Value_Combined"
    )

    id_columns = config["id_columns"]
    field_column = config["field_column"]

    base = merged[id_columns].drop_duplicates()

    wide = merged.pivot_table(
        index=id_columns,
        columns=field_column,
        values="Value_Combined",
        aggfunc="first"
    ).reset_index()

    wide.columns.name = None

    final = base.merge(wide, on=id_columns, how="left")

    sort_columns = [col for col in config.get("sort_columns", []) if col in final.columns]
    if sort_columns:
        final = final.sort_values(sort_columns).reset_index(drop=True)
        final = final.where(pd.notna(final), "")

    if output_file:
        final.to_csv(output_file, index=False, encoding="utf-8-sig")

    return final