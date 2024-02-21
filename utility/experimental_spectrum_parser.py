import re
import pandas as pd
import numpy as np
from collections import Counter


class ExperimentParser:

    @staticmethod
    def guess_delimiter_and_check_table(filename, num_lines=10):
        delimiters = [',', '\t', ';', '|', '    ']  # Common delimiters
        delimiter_counts = {delim: 0 for delim in delimiters}

        lines_sampled = 0
        with open(filename, 'r') as file:
            for i, line in enumerate(file):
                if i == 0:
                    continue  # Skip first line
                if i >= num_lines:
                    break
                line_delim_counts = Counter(line.strip())
                for delim in delimiters:
                    delimiter_counts[delim] += line_delim_counts[delim]
                lines_sampled += 1

        # Identify the most common delimiter
        guessed_delimiter = max(delimiter_counts, key=delimiter_counts.get)
        avg_delimiter_count = delimiter_counts[guessed_delimiter] / lines_sampled

        # Simple heuristic to decide if it's a data table: consistent use of a delimiter
        is_data_table = avg_delimiter_count >= 1  # Expect at least 2 columns
        return guessed_delimiter, is_data_table

    @staticmethod
    def read_file_as_arrays(path, extension, delimiter=None):
        # Determine the file type

        # Read the file based on its extension
        if extension in ['.xlsx', '.xls', '.xlsm', '.xltx', '.xltm']:
            df = pd.read_excel(path)
        elif extension in ['.csv', '.tsv', '.txt']:
            # For CSV/TSV, if no delimiter is specified, default to ',' for CSV and '\t' for TSV
            if delimiter is None:
                delimiter = '\t' if extension == '.tsv' else ','
            df = pd.read_csv(path, delimiter=delimiter)
        elif extension == '.ods':
            df = pd.read_excel(path, engine='odf')
        else:
            raise ValueError("Unsupported file format")

        # Convert to numeric, coercing errors (non-numeric to NaN), then drop rows with NaN
        df = df.apply(pd.to_numeric, errors='coerce').dropna()

        # Return columns as numpy arrays, excluding non-numeric rows
        columns_as_arrays = {col: df[col].to_numpy() for col in df}

        return columns_as_arrays, df.columns.tolist()
