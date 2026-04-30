import re
import pandas as pd
from transformation_common import build_merged_table


def sort_question_columns(cols):
    """
    Sorts question columns so that repeated answers group together by iteration:
        Weight_1, Weight_2, BMI_1, BMI_2  →  BMI_1, BMI_2, Weight_1, Weight_2
    """
    def sort_key(col):
        match = re.match(r"(.*)_(\d+)$", col)
        if match:
            question, num = match.groups()
            return (question, int(num))
        return (col, 0)

    return sorted(cols, key=sort_key)


def process_iterative_files(primary_file, secondary_file, output_file=None):
    """
    Iterative questionnaire workflow.

    The same patient/pathway/content appears MULTIPLE TIMES (one per
    visit or iteration).  Output: one row per patient, with repeated
    question answers suffixed _1, _2, _3 … in chronological order.
    Dates are dropped from the output because they are absorbed into
    the iteration number.

    Example output shape:
        Patient ID | Pathway Name | Content Name | Weight_1 | Weight_2 | BMI_1 | BMI_2
        P001       | Pathway A    | Content X    | 70       | 72       | 22.1  | 22.8
    """
    df = build_merged_table(primary_file, secondary_file)

    id_cols = [col for col in ["Patient ID", "Pathway Name", "Content Name"] if col in df.columns]
    date_cols = [col for col in ["Scheduled date", "Entry Date"] if col in df.columns]

    # Step 1 – pivot to one row per (patient + event), one column per question
    wide_per_event = df.pivot_table(
        index=id_cols + date_cols,
        columns="Question",
        values="Answer_Combined",
        aggfunc="first",
    ).reset_index()

    wide_per_event.columns.name = None

    # Step 2 – sort chronologically so iteration numbers follow time order
    sort_cols = [col for col in id_cols + date_cols if col in wide_per_event.columns]
    wide_per_event = wide_per_event.sort_values(sort_cols).reset_index(drop=True)

    # Step 3 – assign an iteration number per patient group
    iteration_sort = [col for col in date_cols if col in wide_per_event.columns]
    wide_per_event["Iteration"] = (
        wide_per_event
        .sort_values(id_cols + iteration_sort)
        .groupby(id_cols)
        .cumcount() + 1
    )

    # Step 4 – melt back to long (id + iteration | question | value)
    non_value_cols = set(id_cols + date_cols + ["Iteration"])
    value_cols = [col for col in wide_per_event.columns if col not in non_value_cols]

    melted = wide_per_event.melt(
        id_vars=id_cols + ["Iteration"],
        value_vars=value_cols,
        var_name="Question",
        value_name="Value",
    )
    melted = melted.dropna(subset=["Value"])

    # Step 5 – build "Question_N" column names and pivot to final wide shape
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

    # Step 6 – order: id columns first, then question columns sorted by name + iteration
    base_cols = [col for col in id_cols if col in final.columns]
    dynamic_cols = [col for col in final.columns if col not in base_cols]
    final = final[base_cols + sort_question_columns(dynamic_cols)]

    if output_file:
        final.to_csv(output_file, index=False, encoding="utf-8-sig")

    return final
