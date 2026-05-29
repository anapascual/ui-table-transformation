"""
Comprehensive tests for the transformation logic.

Tests validate all the required fixes:
1. Non-responders are included
2. All answers are preserved (no overwriting)
3. Column names are stable and clean
4. Validation checks work
"""

import os
import sys
import tempfile
import unittest
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app')))
import transformation_iterative as ti
import transformation_normal as tn


class TestNonResponders(unittest.TestCase):
    """Test that non-responders are included in the output."""
    
    def test_non_responders_included_in_iterative(self):
        """Non-responders should appear in output with blank answer columns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            content_path = os.path.join(tmpdir, 'content.csv')
            answers_path = os.path.join(tmpdir, 'answers.csv')
            
            # Create content with 2 patients
            content = pd.DataFrame([
                {'Patient ID': 1, 'Pathway Name': 'P1', 'Content Name': 'Q1', 'Entry Date': '2025-01-01'},
                {'Patient ID': 2, 'Pathway Name': 'P1', 'Content Name': 'Q1', 'Entry Date': '2025-01-01'},
            ])
            
            # Create answers for only 1 patient (Patient 1)
            answers = pd.DataFrame([
                {'Patient ID': 1, 'Pathway Name': 'P1', 'Content Name': 'Q1', 'Entry Date': '2025-01-01', 'Question': 'Q', 'Answer Text': pd.NA, 'Answer Value': 'A'},
            ])
            
            content.to_csv(content_path, index=False)
            answers.to_csv(answers_path, index=False)
            
            result = ti.process_iterative_files(content_path, answers_path)
            
            # Both patients should be in the output
            self.assertEqual(result.shape[0], 2)
            
            # Patient 2 (non-responder) should have an empty answer column
            patient2 = result[result['Patient ID'].astype(str) == '2']
            self.assertEqual(patient2.shape[0], 1)
            # The only non-ID column should be the answer column, which should be NaN
            answer_cols = [col for col in patient2.columns if col not in ['Patient ID', 'Pathway Name']]
            if answer_cols:
                self.assertTrue(patient2[answer_cols[0]].isna().all())


class TestAnswerPreservation(unittest.TestCase):
    """Test that all answers are preserved without overwriting."""
    
    def test_repeated_questionnaires_not_overwritten(self):
        """Multiple iterations of the same question should not overwrite each other."""
        with tempfile.TemporaryDirectory() as tmpdir:
            content_path = os.path.join(tmpdir, 'content.csv')
            answers_path = os.path.join(tmpdir, 'answers.csv')
            
            content = pd.DataFrame([
                {'Patient ID': 1, 'Pathway Name': 'P1', 'Content Name': 'Allgemeine Gesundheit', 'Entry Date': '2025-01-01'},
                {'Patient ID': 1, 'Pathway Name': 'P1', 'Content Name': 'Allgemeine Gesundheit', 'Entry Date': '2025-01-02'},
                {'Patient ID': 1, 'Pathway Name': 'P1', 'Content Name': 'Allgemeine Gesundheit', 'Entry Date': '2025-01-03'},
            ])
            
            # Same question answered 3 times on different dates
            answers = pd.DataFrame([
                {'Patient ID': 1, 'Pathway Name': 'P1', 'Content Name': 'Allgemeine Gesundheit', 'Entry Date': '2025-01-01', 'Question': 'Q', 'Answer Text': pd.NA, 'Answer Value': 'A1'},
                {'Patient ID': 1, 'Pathway Name': 'P1', 'Content Name': 'Allgemeine Gesundheit', 'Entry Date': '2025-01-02', 'Question': 'Q', 'Answer Text': pd.NA, 'Answer Value': 'A2'},
                {'Patient ID': 1, 'Pathway Name': 'P1', 'Content Name': 'Allgemeine Gesundheit', 'Entry Date': '2025-01-03', 'Question': 'Q', 'Answer Text': pd.NA, 'Answer Value': 'A3'},
            ])
            
            content.to_csv(content_path, index=False)
            answers.to_csv(answers_path, index=False)
            
            result = ti.process_iterative_files(content_path, answers_path)
            
            # Should have 3 columns: Patient ID, Pathway Name, Q_Allgemeine Gesundheit_1, Q_Allgemeine Gesundheit_2, Q_Allgemeine Gesundheit_3
            expected_cols = {'Patient ID', 'Pathway Name', 'Q_Allgemeine Gesundheit_1', 'Q_Allgemeine Gesundheit_2', 'Q_Allgemeine Gesundheit_3'}
            self.assertTrue(expected_cols.issubset(set(result.columns)), f"Missing expected columns. Got: {set(result.columns)}")
            
            # Each should have the correct answer
            row = result.iloc[0]
            self.assertEqual(row['Q_Allgemeine Gesundheit_1'], 'A1')
            self.assertEqual(row['Q_Allgemeine Gesundheit_2'], 'A2')
            self.assertEqual(row['Q_Allgemeine Gesundheit_3'], 'A3')


class TestColumnNameStability(unittest.TestCase):
    """Test that column names are stable and clean."""
    
    def test_column_names_are_unique(self):
        """No duplicate column names should exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            content_path = os.path.join(tmpdir, 'content.csv')
            answers_path = os.path.join(tmpdir, 'answers.csv')
            
            content = pd.DataFrame([
                {'Patient ID': 1, 'Pathway Name': 'P1', 'Content Name': 'Q1', 'Entry Date': '2025-01-01'},
                {'Patient ID': 1, 'Pathway Name': 'P1', 'Content Name': 'Q1', 'Entry Date': '2025-01-02'},
            ])
            
            answers = pd.DataFrame([
                {'Patient ID': 1, 'Pathway Name': 'P1', 'Content Name': 'Q1', 'Entry Date': '2025-01-01', 'Question': 'Q', 'Answer Text': pd.NA, 'Answer Value': 'A1'},
                {'Patient ID': 1, 'Pathway Name': 'P1', 'Content Name': 'Q1', 'Entry Date': '2025-01-02', 'Question': 'Q', 'Answer Text': pd.NA, 'Answer Value': 'A2'},
            ])
            
            content.to_csv(content_path, index=False)
            answers.to_csv(answers_path, index=False)
            
            result = ti.process_iterative_files(content_path, answers_path)
            
            # Check for duplicate column names
            duplicates = result.columns[result.columns.duplicated()].tolist()
            self.assertEqual(len(duplicates), 0, f"Duplicate columns found: {duplicates}")
    
    def test_column_names_are_clean(self):
        """Column names should have whitespace normalized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            content_path = os.path.join(tmpdir, 'content.csv')
            answers_path = os.path.join(tmpdir, 'answers.csv')
            
            # Questions with extra whitespace and punctuation
            content = pd.DataFrame([
                {'Patient ID': 1, 'Pathway Name': 'P1', 'Content Name': 'TestContent', 'Entry Date': '2025-01-01'},
            ])
            
            answers = pd.DataFrame([
                {'Patient ID': 1, 'Pathway Name': 'P1', 'Content Name': 'TestContent', 'Entry Date': '2025-01-01', 'Question': '  Q1  ?  ', 'Answer Text': pd.NA, 'Answer Value': 'A'},
            ])
            
            content.to_csv(content_path, index=False)
            answers.to_csv(answers_path, index=False)
            
            result = ti.process_iterative_files(content_path, answers_path)
            
            # Column name should be clean: 'Q1_TestContent' (not '  Q1  ?  _TestContent')
            self.assertIn('Q1_TestContent', result.columns)


class TestValidation(unittest.TestCase):
    """Test that validation checks work correctly."""
    
    def test_output_has_all_patient_pathway_combinations(self):
        """Output should include all patient-pathway combinations from content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            content_path = os.path.join(tmpdir, 'content.csv')
            answers_path = os.path.join(tmpdir, 'answers.csv')
            
            # 3 patient-pathway combinations
            content = pd.DataFrame([
                {'Patient ID': 1, 'Pathway Name': 'P1', 'Content Name': 'Q1', 'Entry Date': '2025-01-01'},
                {'Patient ID': 2, 'Pathway Name': 'P1', 'Content Name': 'Q1', 'Entry Date': '2025-01-01'},
                {'Patient ID': 3, 'Pathway Name': 'P1', 'Content Name': 'Q1', 'Entry Date': '2025-01-01'},
            ])
            
            # Only 2 have answers
            answers = pd.DataFrame([
                {'Patient ID': 1, 'Pathway Name': 'P1', 'Content Name': 'Q1', 'Entry Date': '2025-01-01', 'Question': 'Q', 'Answer Text': pd.NA, 'Answer Value': 'A'},
                {'Patient ID': 2, 'Pathway Name': 'P1', 'Content Name': 'Q1', 'Entry Date': '2025-01-01', 'Question': 'Q', 'Answer Text': pd.NA, 'Answer Value': 'B'},
            ])
            
            content.to_csv(content_path, index=False)
            answers.to_csv(answers_path, index=False)
            
            result = ti.process_iterative_files(content_path, answers_path)
            
            # All 3 should be in output
            self.assertEqual(result.shape[0], 3)
            
            # Verify all patient IDs are present (converted to strings by CSV)
            patient_ids = set(str(p) for p in result['Patient ID'].values)
            self.assertEqual(patient_ids, {'1', '2', '3'})


class TestNormalWorkflow(unittest.TestCase):
    """Test the normal (non-iterative) workflow."""
    
    def test_normal_workflow_includes_non_responders(self):
        """Normal workflow should also include non-responders."""
        with tempfile.TemporaryDirectory() as tmpdir:
            content_path = os.path.join(tmpdir, 'content.csv')
            answers_path = os.path.join(tmpdir, 'answers.csv')
            
            content = pd.DataFrame([
                {'Patient ID': 1, 'Pathway Name': 'P1', 'Content Name': 'C1', 'Entry Date': '2025-01-01'},
                {'Patient ID': 2, 'Pathway Name': 'P1', 'Content Name': 'C1', 'Entry Date': '2025-01-01'},
            ])
            
            answers = pd.DataFrame([
                {'Patient ID': 1, 'Pathway Name': 'P1', 'Content Name': 'C1', 'Entry Date': '2025-01-01', 'Question': 'Q', 'Answer Text': pd.NA, 'Answer Value': 'A'},
            ])
            
            content.to_csv(content_path, index=False)
            answers.to_csv(answers_path, index=False)
            
            result = tn.process_normal_files(content_path, answers_path)
            
            # Both patients should be in output
            self.assertEqual(result.shape[0], 2)
            
            # Patient 2 should have blank answer columns
            patient2 = result[result['Patient ID'].astype(str) == '2']
            self.assertEqual(patient2.shape[0], 1)


if __name__ == '__main__':
    unittest.main()
