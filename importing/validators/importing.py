import csv
import datetime as dt
import enum
from pathlib import Path

import smart_open


class ImportDirValidator:
    """
    Validate the directory structure for importing data.

    The source directory to import data from. Source directory structure:
    ```
    <Source-Dir>/
    ├── Accounts.csv
    └── Transactions/
        ├── <Account-AccountID>_<YYYY>-<mm>.csv
        ├── ...
        └── <Account-AccountID>_<YYYY>-<mm>.csv
    ```
    """

    def __init__(self, directory: Path):
        self.directory: Path = directory

    def is_valid(self) -> str:
        """Return non-empty error message if the directory structure is valid, else empty string."""

        if not self.directory.is_dir():
            return f"Source directory {self.directory} is not a directory or does not exist."

        # Check for required files
        required_files = {
            "Accounts.csv": True,
            "Transactions": False,
        }

        for path, should_be_file in required_files.items():
            if not (self.directory / path).exists():
                return f"Required file or directory {path} is missing."

            if should_be_file and not (self.directory / path).is_file():
                return f"Required file {path} is not a file."

        return ""


class AccountInstitution(enum.StrEnum):
    koho = "koho"
    td_canada = "td_canada"


class AccountFileValidator:
    """
    Validate the account files in the Transactions directory.

    The expected account file name format is:
    ```
    <Account-AccountID>_<YYYY>-<mm>-<dd>.csv
    ```
    The expected columns in the file are:
    ```
    - AccountID: str
    - Name: str
    - Institution: str
    - AmountInitial: float
    - DateStart: YYYY-MM-DD
    ```
    """

    # TODO @imranariffin: Use a schema validation library like pydantic or cerberus
    # to validate the CSV file structure and data types.

    COLUMNS_EXPECTED = {
        "AccountID": str,
        "Name": str,
        "Institution": str,
        "AmountInitial": float,
        "DateStart": dt.date,
    }

    def __init__(self, source_dir: Path):
        self.file_path: Path = source_dir / "Accounts.csv"

    def is_valid(self) -> str:
        """Return non-empty error message if the account file is invalid, else empty string."""

        if not self.file_path.is_file():
            return f"Account file {self.file_path} is not a file or does not exist."

        with smart_open.open(self.file_path, "r") as fi:
            reader = csv.DictReader(fi)

            # Validate column names
            column_names: set[str] = set(reader.fieldnames or [])
            for column_name_expected in self.COLUMNS_EXPECTED.keys():
                if column_name_expected not in column_names:
                    return f"Missing required column in account file {self.file_path}: {column_name_expected}"

            # Validate each row
            for i, row in enumerate(reader):
                for column_name, column_type in self.COLUMNS_EXPECTED.items():
                    value = row[column_name]
                    if column_type == float:
                        try:
                            float(value)
                        except ValueError:
                            return (
                                f"Row {i}: Invalid float value for column {column_name} "
                                f"in account file {self.file_path}: {value}"
                            )
                    elif column_type == dt.date:
                        try:
                            dt.datetime.strptime(value, "%Y-%m-%d").date()
                        except ValueError:
                            return (
                                f"Row {i}: Invalid date value for column {column_name} "
                                f"in account file {self.file_path}: {value}"
                            )
                    elif column_type == str:
                        if not isinstance(value, str):
                            return (
                                f"Row {i}: Invalid string value for column {column_name} "
                                f"in account file {self.file_path}: {value}"
                            )
                    else:
                        return (
                            f"Unsupported column type {column_type} for column {column_name} "
                            f"in account file {self.file_path}"
                        )

        return ""


class ImportTransactionDirValidator:
    """
    Validate the structure of the Transactions directory.

    The expected file name format is:
    ```
    <Account-AccountID>_<YYYY>-<mm>.csv
    ```
    """

    def __init__(self, source_dir: Path) -> None:
        self.path = source_dir / "Transactions"

    def is_valid(self) -> str:
        """Return non-empty error message if the directory structure is invalid, else empty string."""

        # Check for required files
        for file in self.path.glob("*.csv"):
            if not file.name.endswith(".csv"):
                return f"Non-CSV file found in directory {self.path}: {file.name}"

            if not self._is_valid_transaction_file_name(file.name):
                return f"Invalid transaction file name in directory {self.path}: {file.name}"

        return ""

    def _is_valid_transaction_file_name(self, file_name: str) -> bool:
        """Check if the transaction file name matches the expected format."""
        date_str = file_name.rsplit("_", maxsplit=1)[-1].removesuffix(".csv")
        try:
            dt.datetime.strptime(date_str, "%Y-%m").date()
            return True
        except ValueError:
            return False
