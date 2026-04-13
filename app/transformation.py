import pandas as pd

def process_files(schedule_file, answers_file, output_file=None):
    schedule = pd.read_csv(schedule_file)
    answers = pd.read_csv(answers_file)

    if "Input date" in schedule.columns:
        schedule = schedule.rename(columns={"Input date": "Entry Date"})

    final_table = pd.merge(schedule, answers, on="Entry Date", how="left")

    final_table = final_table.loc[:, ~final_table.columns.str.endswith("_y")]
    final_table.columns = final_table.columns.str.replace("_x", "", regex=False)

    if "Answer Value" in final_table.columns or "Answer Text" in final_table.columns:
        answer_value = (
            final_table["Answer Value"]
            if "Answer Value" in final_table.columns
            else pd.Series(index=final_table.index, dtype="object")
        )
        answer_text = (
            final_table["Answer Text"]
            if "Answer Text" in final_table.columns
            else pd.Series(index=final_table.index, dtype="object")
        )
        final_table["Answer_Combined"] = answer_value.fillna(answer_text)

    id_columns = [
        col
        for col in ["Patient ID", "Pathway Name", "Content Name", "Scheduled date", "Entry Date"]
        if col in final_table.columns
    ]

    if "Question" in final_table.columns and "Answer_Combined" in final_table.columns:
        pivot_table = final_table.pivot_table(
            index=id_columns,
            columns="Question",
            values="Answer_Combined",
            aggfunc="first"
        ).reset_index()

        pivot_table.columns.name = None
        final_table = pivot_table

    sort_cols = [col for col in ["Patient ID", "Scheduled date", "Entry Date"] if col in final_table.columns]
    if sort_cols:
        final_table = final_table.sort_values(by=sort_cols).reset_index(drop=True)

    if "Patient ID" in final_table.columns:
        final_table["Iteration"] = final_table.groupby("Patient ID").cumcount() + 1

    if output_file:
        final_table.to_csv(output_file, index=False)

    return final_table