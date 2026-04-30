import pandas as pd
from transformation_common import build_merged_table


def process_normal_files(primary_file, secondary_file, output_file=None):
    """
    Normal (non-iterative) questionnaire workflow.

    Each patient/pathway/content appears only ONCE in the input data.
    Output: one row per questionnaire event, with Scheduled date and
    Entry Date included, and one column per question.

    Example output shape:
        Patient ID | Pathway Name | Content Name | Scheduled date | Entry Date | Q1 | Q2 | Q3
        P001       | Pathway A    | Content X    | 2024-01-10     | 2024-01-11 | 5  | Yes| 3
    """
    df = build_merged_table(primary_file, secondary_file)

    id_cols = [col for col in ["Patient ID", "Pathway Name", "Content Name"] if col in df.columns]
    date_cols = [col for col in ["Scheduled date", "Entry Date"] if col in df.columns]

    final = df.pivot_table(
        index=id_cols + date_cols,
        columns="Question",
        values="Answer_Combined",
        aggfunc="first",
    ).reset_index()

    final.columns.name = None

    if output_file:
        final.to_csv(output_file, index=False, encoding="utf-8-sig")

    return final
