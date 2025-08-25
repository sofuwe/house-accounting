from pathlib import Path


class ImportDirParserValidator:
    def __init__(self, source_dir: Path) -> None:
        self.source_dir = source_dir

    def is_valid(self) -> str:
        """Return non-empty error message if the directory structure is valid, else empty string."""
        if not self.source_dir.is_dir():
            return f"Source directory {self.source_dir} is not a directory or does not exist."

        # Check for non-CSV files and invalid file names
        for file in self.source_dir.glob("*"):
            if file.is_dir():
                continue

            if not file.name.endswith(".csv"):
                return f"Non-CSV file found in source directory: {file.name}"

        return ""
