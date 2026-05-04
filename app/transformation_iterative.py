import re
import pandas as pd
from transformation_common import build_merged_table


def sort_question_columns(cols):
    def sort_key(col):
        match = re.match(r"(.*)_(\d+)$", col)
        if match:
            question, num = match.groups()
            return (question, int(num))
        return (col, 0)
    return sorted(cols, key=sort_key)


def _fill_sentinel(series, sentinel_ts, sentinel_str):
    """Fill NaN/NaT regardless of whether the column is datetime or object/str."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return series.fillna(sentinel_ts)
    else:
        return series.fillna(sentinel_str)


def _restore_sentinel(series, sentinel_ts, sentinel_str):
    """Put NaN/NaT back after pivot."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return series.replace(sentinel_ts, pd.NaT)
    else:
        return series.replace(sentinel_str, pd.NA)


def process_iterative_files(primary_file, secondary_file, output_file=None):
    """
    Iterative questionnaire workflow.

    Output: one row per patient, with repeated question answers suffixed
    _1, _2, _3 … in chronological order by Entry Date.

    Rows where Scheduled date (or any other date) is missing are fully
    preserved — NaT/NaN is replaced with a sentinel before pivoting so
    pandas does not silently discard those rows.
    """
    df = build_merged_table(primary_file, secondary_file)

    id_cols   = [col for col in ["Patient ID", "Pathway Name", "Content Name"] if col in df.columns]
    date_cols = [col for col in ["Scheduled date", "Entry Date"] if col in df.columns]

    SENTINEL_TS  = pd.Timestamp("1900-01-01")
    SENTINEL_STR = "___MISSING___"

    # ── Step 1: pivot to one row per event, keeping NaN rows via sentinel ──
    df_pivot = df.copy()
    for col in date_cols:
        df_pivot[col] = _fill_sentinel(df_pivot[col], SENTINEL_TS, SENTINEL_STR)

    wide_per_event = df_pivot.pivot_table(
        index=id_cols + date_cols,
        columns="Question",
        values="Answer_Combined",
        aggfunc="first",
    ).reset_index()
    wide_per_event.columns.name = None

    # Restore sentinels to NaN/NaT
    for col in date_cols:
        wide_per_event[col] = _restore_sentinel(wide_per_event[col], SENTINEL_TS, SENTINEL_STR)

    # ── Step 2: sort by Entry Date (NaT last) so iteration order follows time ──
    sort_key_col = "Entry Date" if "Entry Date" in wide_per_event.columns else (date_cols[0] if date_cols else None)
    if sort_key_col:
        wide_per_event = (
            wide_per_event
            .sort_values(id_cols + [sort_key_col], na_position="last")
            .reset_index(drop=True)
        )

    # ── Step 3: assign iteration number per patient group ──
    wide_per_event["Iteration"] = (
        wide_per_event.groupby(id_cols).cumcount() + 1
    )

    # ── Step 4: melt back to long format ──
    non_value_cols = set(id_cols + date_cols + ["Iteration"])
    value_cols = [col for col in wide_per_event.columns if col not in non_value_cols]

    melted = wide_per_event.melt(
        id_vars=id_cols + ["Iteration"],
        value_vars=value_cols,
        var_name="Question",
        value_name="Value",
    )
    melted = melted.dropna(subset=["Value"])

    # ── Step 5: build Question_N column names and pivot to final wide shape ──
    melted["Question_Iteration"] = (
        melted["Question"].astype(str).str.strip()
        + "_"
        + melted["Iteration"].astype(str)
    )

    final = melted.pivot_table(
        index=id_cols,
        columns="Question_Iteration",
        values="Value",
        aggfunc="first",
    ).reset_index()
    final.columns.name = None

    # ── Step 6: order columns ──
    base_cols    = [col for col in id_cols if col in final.columns]
    dynamic_cols = [col for col in final.columns if col not in base_cols]
    final = final[base_cols + sort_question_columns(dynamic_cols)]

    if output_file:
        final.to_csv(output_file, index=False, encoding="utf-8-sig")

    return final
