"""
This is an append-only CSV-backed dictionary.
"""

import csv

class SyncedCSVDict(object):
    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.internal_dict = {}
        # Initialize internal dictionary from the CSV
        with open(csv_path, 'r') as f:
            csvreader = csv.reader(f)
            for row in csvreader:
                assert len(row) == 2
                key = row[0]
                val = row[1]
                self.internal_dict[key] = val

    def has_key(self, key):
        return key in self.internal_dict

    def get_val(self, key):
        return self.internal_dict[key]

    def set_val(self, key, val):
        assert key not in self.internal_dict
        with open(self.csv_path, 'a') as f:
            csvwriter = csv.writer(f)
            csvwriter.writerow([key, val])
        self.internal_dict[key] = val
