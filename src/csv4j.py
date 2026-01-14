#!/usr/bin/env python3
"""
csv4j - lightweight CSV from json tool

This script extracts tabular data from JSON using a simple YAML template
and writes a CSV-like output.
"""

import argparse
import sys
import logging
from pathlib import Path
import yaml  # type: ignore
import json
from typing import TypedDict
import time
import re

# Add a custom TRACE level (below DEBUG) for very verbose diagnostics.
TRACE_LEVEL_NUM = 9
logging.addLevelName(TRACE_LEVEL_NUM, "TRACE")


def _logger_trace(self, message, *args, **kws) -> None:
    """Log a message at TRACE level.

    Args:
        self (logging.Logger): Logger instance.
        message (str): Message to log.
        *args: Format arguments (tuple).
        **kws: Additional keyword arguments (dict).
    """
    # Instance method for Logger.trace(); respects logger's enabled level
    if self.isEnabledFor(TRACE_LEVEL_NUM):
        self._log(TRACE_LEVEL_NUM, message, args, **kws)


if not hasattr(logging.Logger, "trace"):
    # Attach the trace level method to the standard Logger class
    logging.Logger.trace = _logger_trace  # type: ignore


def trace(msg, *args, **kws) -> None:
    """Log a message at TRACE level (module-level convenience function).

    Args:
        msg (str): Message to log.
        *args: Format arguments (tuple).
        **kws: Additional keyword arguments (dict).
    """
    # Convenience module-level function mirroring other logging methods
    logging.log(TRACE_LEVEL_NUM, msg, *args, **kws)


logging.trace = trace  # type: ignore


class Template:
    """Represents a YAML template for CSV extraction from JSON.

    This class manages template validation against a JSON schema and provides
    the schema definition for valid templates.
    """

    structure = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "csv4j template schema",
        "description": "Schema for the YAML template used by csv4j (validate with jsonschema)",
        "type": "object",
        "properties": {
            "tables": {"type": "array", "items": {"$ref": "#/definitions/table"}},
            "pipes": {"type": "object", "items": {"$ref": "#/definitions/pipes"}},
        },
        "additionalProperties": False,
        "definitions": {
            "table": {
                "type": "object",
                "description": "A table extraction definition",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Human-readable table name",
                    },
                    "path": {
                        # Allow either a string path or a null value so templates
                        # can explicitly omit paths when appropriate.
                        "type": ["string", "null"],
                        "description": "JSON path (slash or // separated) to the array/object to extract",
                    },
                    "body": {
                        "type": "object",
                        "description": "Mapping of column keys to JSON paths (string)",
                        "minProperties": 1,
                        "additionalProperties": {"type": "string"},
                    },
                },
                "required": ["body"],
                "additionalProperties": False,
            },
            "pipes": {
                "type": "object",
                "description": "A pipe of the size of the entire table",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
    }

    def __init__(self, path: Path) -> None:
        """Initialize Template with a YAML file path.

        Args:
            path (pathlib.Path): Path to the YAML template file.
        """
        # The template YAML file path that describes table extraction rules
        self.path = path

    def validate(self) -> None:
        """Validate the YAML template against the schema.

        Args:
            None

        Raises:
            jsonschema.ValidationError: If the template does not conform to the schema.
        """
        from jsonschema import validate

        # Validate the YAML template against the embedded JSON schema
        schema = self.structure
        tpl = yaml.safe_load(open(self.path, "r", encoding="utf-8"))
        validate(instance=tpl, schema=schema)


class Logger(logging.Logger):
    """Custom logger with support for TRACE level and dual output streams.

    Logs to both a file (csv4j.log) and console with configurable verbosity.
    """

    def __init__(self, name, level=0, verbose=0) -> None:
        """Initialize the Logger with specified verbosity level.

        Args:
            name (str): Logger name.
            level (int): Base logging level (default: 0).
            verbose (int): Verbosity count where 0=INFO, 1=DEBUG, 2+=TRACE (default: 0).
        """
        super().__init__(name, level)
        # configure logging on this logger instance
        logger = self
        logger.setLevel(TRACE_LEVEL_NUM)

        # File handler always records detailed logs to `csv4j.log` so users
        # can inspect trace/debug information after a run.
        file_handler = logging.FileHandler("csv4j.log", encoding="utf-8")
        # file captures TRACE when at least one -v, otherwise DEBUG
        file_handler.setLevel(TRACE_LEVEL_NUM if verbose >= 1 else logging.DEBUG)
        # pad levelname to 8 chars so columns align regardless of level
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-8s %(message)s")
        )

        # Console handler prints concise messages to stdout. Verbosity on
        # console is controlled by the `-v` count: none => INFO, -v => DEBUG,
        # -vv+ => TRACE for live debugging.
        console_handler = logging.StreamHandler(sys.stdout)
        if verbose >= 2:
            console_level = TRACE_LEVEL_NUM
        elif verbose == 1:
            console_level = logging.DEBUG
        else:
            console_level = logging.INFO
        console_handler.setLevel(console_level)
        console_handler.setFormatter(logging.Formatter("%(levelname)-8s: %(message)s"))

        # prevent adding duplicate handlers if main called multiple times
        if not logger.handlers:
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)

        # record initialization details at debug level
        logger.debug("Logger initialized with verbosity %d", verbose)


def parse_args(argv=None):
    """Parse command-line arguments.

    Args:
        argv (list[str] | None): List of arguments to parse (default: None, uses sys.argv).

    Returns:
        argparse.Namespace: Parsed arguments with attributes: input, output, template, verbose, sep, multiline.
    """
    parser = argparse.ArgumentParser(prog="csv4j", description="CSV utility")
    parser.add_argument(
        "-i",
        "--input",
        help="Input CSV file (default: stdin)",
        metavar="INPUT",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output file (default: stdout)",
        metavar="OUTPUT",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="Increase verbosity (-v for debug, -vv for trace on stdout)",
        action="count",
        default=0,
        required=False,
    )
    parser.add_argument(
        "-t",
        "--template",
        help="Template file to use",
        metavar="TEMPLATE",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "-s",
        "--sep",
        help="CSV separator character (default: ',')",
        metavar="SEP",
        choices=[",", "|", ";"],
        default=",",
        required=False,
    )
    parser.add_argument(
        "-ml",
        "--multiline",
        help="When set, list-type cells are emitted as multiple lines (each prefixed with '-'). Otherwise lists are joined inline.",
        action="store_true",
        required=False,
    )
    return parser.parse_args(argv)


class Boilerplate(TypedDict):
    name: str
    ncols: int
    nrows: int
    header: list[str]
    rows: list[list[str]]


class Csv4J:
    """Main class for extracting CSV data from JSON using a YAML template.

    This class coordinates the extraction process, validates inputs, and manages
    the output generation.
    """

    def __init__(
        self, input_path: Path, output_path: Path, template_path: Path, verbose: int = 0
    ) -> None:
        """Initialize Csv4J processor.

        Args:
            input_path (pathlib.Path): Path to the input JSON file.
            output_path (pathlib.Path): Path to the output CSV file.
            template_path (pathlib.Path): Path to the YAML template file.
            verbose (int): Verbosity level for logging (default: 0).
        """
        print("csv4j - lightweight CSV from json tool")
        # initialize module logger with desired verbosity
        self.logger = Logger("csv4j", verbose=verbose)
        # normalize provided paths to Path objects
        self.input_path = Path(input_path)
        self.template_path = Path(template_path)
        self.output_path = Path(output_path)
        # Validate that the input/template files exist and have expected ext
        self.validate_paths()

    def validate_paths(self) -> bool:
        """Validate that input and template files exist with correct extensions.

        Args:
            None

        Returns:
            bool: True if validation failed, False if all checks passed.
        """
        errors = 0
        if not self.input_path.exists() or not self.input_path.is_file():
            self.logger.error(
                "input file '%s' does not exist or is not a file", self.input_path
            )
            errors += 1
        if self.input_path.suffix.lower() != ".json":
            self.logger.error(
                "input file '%s' must have a .json extension", self.input_path
            )
            errors += 1
        if not self.template_path.exists() or not self.template_path.is_file():
            self.logger.error(
                "template file '%s' does not exist or is not a file", self.template_path
            )
            errors += 1
        if self.template_path.suffix.lower() != ".yaml":
            self.logger.error(
                "template file '%s' must have a .yaml extension", self.template_path
            )
            errors += 1

        # Return True if there were validation errors (convenience for caller)
        if errors > 0:
            self.logger.error("validation failed with %d error(s), exiting", errors)
            return True
        else:
            self.logger.debug("all input files validated successfully")
            return False

    def process(self, sep: str = ",", multiline: bool = False) -> None:
        """Process JSON input using the template and write CSV output.

        Args:
            sep (str): CSV separator character (default: ',').
            multiline (bool): If True, list items are emitted as multiple lines.
                            If False, lists are joined inline (default: False).
        """
        start = time.perf_counter()

        # Load JSON input
        with open(self.input_path, "r", encoding="utf-8") as f:
            in_stream = json.load(f)
            if type(in_stream) is dict:
                self.logger.trace(  # type: ignore[attr-defined]
                    f"input JSON loaded successfully as dictionary with {len(in_stream)} top-level keys"
                )
            elif type(in_stream) is list:
                in_stream = {".": in_stream}
                self.logger.trace(  # type: ignore[attr-defined]
                    f"input JSON loaded successfully as list with {len(in_stream)} top-level entries"
                )
            else:
                self.logger.error(
                    "warning: input JSON is neither an object nor an array"
                )

        # Open output stream for writing text CSV-like payload
        out_stream = open(self.output_path, "w", encoding="utf-8")

        # Load the YAML template that defines tables and column mappings
        template = yaml.safe_load(self.template_path.read_text(encoding="utf-8"))

        # Accumulate per-table intermediate payloads and track max dimensions
        table_payload = []  # type: ignore[var-annotated]
        max_rows = -1
        max_cols = -1

        for table in template.get("tables", []):
            # Start blob at root of the JSON input copy so we can drill down
            blob = {**in_stream}

            boilerplate: Boilerplate = {
                "name": table.get("name", "<unnamed>"),
                "ncols": -1,
                "nrows": -1,
                "header": [],
                "rows": [],
            }

            # head = table.get("head", None)
            body = table.get("body", [])

            # The `body` mapping keys become the CSV header for this table
            for header_key in body.keys():
                boilerplate["header"].append(header_key)
            boilerplate["ncols"] = len(boilerplate["header"])  # type: ignore[assignment]

            # Template `path` is expressed as steps separated by '//' to drill
            # into nested objects/arrays in the input JSON.
            path = table.get("path", None)

            recursive_results = (
                self.__recursive_process_path(blob, path) if path else [blob]
            )
            # print(f"final blob: {blob}")
            for blob in recursive_results:
                if blob is None:
                    # Missing path — skip this table and warn user
                    self.logger.warning(
                        f"warning: path '{path}' not found in input JSON"
                    )
                    continue
                else:
                    boilerplate = self.__boilerplate_merge(
                        table_payload, boilerplate, table
                    )
                    self.__process_table(boilerplate=boilerplate, blob=blob, body=body, sep=sep, multiline=multiline)  # type: ignore[union-attr]

            max_cols = max(max_cols, boilerplate["ncols"])  # type: ignore[assignment]
            max_rows = max(max_rows, boilerplate["nrows"])  # type: ignore[assignment]

            table_payload.append(boilerplate)
            self.logger.debug(f"boilerplate: {boilerplate}")  # type: ignore[attr-defined]
            self.logger.info(f"{boilerplate['name']} table done.")

        self.logger.debug(f"max rows: {max_rows}, max cols: {max_cols}")

        if len(template.get("pipes", {})) > 0:
            self.logger.info("starting pipes processing")
            for pipe_k, pipe_v in template.get("pipes", {}).items():
                self.logger.info(f"processing pipe: {pipe_k}")
                dump = set(self.__recursive_process_path(in_stream, pipe_v))
                if len(dump) == 1:
                    pass
                elif len(dump) > 1:
                    self.logger.warning(
                        f"pipe '{pipe_k}' produced multiple values; only the first will be used"
                    )
                    dump = set(list(dump)[:1])
                else:
                    self.logger.warning(
                        f"pipe '{pipe_k}' produced no values; using NONE string"
                    )
                    dump = set(["NONE"])
                pipe_boilerplate: Boilerplate = {
                    "name": pipe_k,
                    "ncols": 1,
                    "nrows": max_rows,
                    "header": [pipe_k],
                    "rows": [[list(dump)[0]]] * max_rows,
                }
                self.logger.debug(f"pipe boilerplate: {pipe_boilerplate}")
                table_payload.append(pipe_boilerplate)

        # Compose final CSV-like payload. Each row index across all matrices
        # is concatenated with the separator character. The final trailing separator
        # is preserved to maintain a predictable shape in the dump output.
        payload = self.__merge_out_tables(table_payload, max_rows, sep)

        out_stream.write(payload)
        out_stream.close()
        self.logger.info(f"output written to '{self.output_path}'")
        # code to measure
        end = time.perf_counter()

        elapsed = end - start
        self.logger.info(f"csv4j processing completed in {elapsed:.4f} seconds")

    def __recursive_process_path(self, blob, path, wildcard={}):
        """Recursively process a JSON path with wildcard support.

        Args:
            blob (dict): The JSON object/dict to process.
            path (str): The path string with steps separated by '//'.
            wildcard (dict): Dictionary of wildcard captures (default: {}).

        Returns:
            list[dict]: List of processed blob dictionaries.
        """
        # Recursively process a path within a blob
        payload = []
        self.logger.trace(
            f"\nresursive at start: {blob}, path: {path}, wildcard: {wildcard}"
        )
        for step in path.split("//"):
            self.logger.trace(
                f"\nresursive at step: {blob}, path: {path}, wildcard: {wildcard}"
            )
            path = "//".join(path.split("//")[1:])
            if step in blob:
                blob = blob[step]
            elif step == "*":
                # Wildcard step: capture all values at this level as a list
                # blob = list(blob.values())
                for k, b in blob.items():
                    # wildcard[f"${len(wildcard.keys())}$"] = k
                    payload += self.__recursive_process_path(
                        b, path, {**wildcard, f"${len(wildcard.keys())}$": k}
                    )
                blob = None
                break
            elif step == "" or step is None:
                break
            else:
                blob = None
                continue

        if type(blob) is dict:
            # print(blob)
            for b in [x for x in blob.values() if type(x) is dict]:
                b.update(wildcard)

        if blob is not None:
            payload.append(blob)

        self.logger.trace(  # type: ignore[attr-defined]
            f"recursive_process_path returning payload {payload} entries"
        )
        return payload

    def __merge_out_tables(self, tables, max_rows, sep):
        """Merge multiple tables into a single CSV-like output string.

        Args:
            tables (list[Boilerplate]): List of table payloads to merge.
            max_rows (int): Maximum number of rows across all tables.
            sep (str): CSV separator character.

        Returns:
            str: CSV-formatted string with tables concatenated horizontally.
        """
        # Convert each table_payload item into a CSV-like matrix. Tables are
        # normalized to the same shape (max_rows x max_cols) so they can be
        # concatenated horizontally into a single output layout.
        payload = ""
        main_matrix = []
        for tbl in tables:
            ncols = tbl.get("ncols", 0)
            nrows = tbl.get("nrows", 0)
            head = list(tbl.get("header", []))  # type: ignore[arg-type]

            # Convert headers to strings; padding is intentionally minimal
            padded_header = [str(h) for h in head]

            # Build matrix containing header row + data rows
            matrix = [padded_header]
            for r in range(max_rows):
                if r < nrows:  # type: ignore[operator]
                    row = tbl.get("rows", [])[r]  # type: ignore[operator, index]
                    # Convert None values to empty strings for CSV output
                    row_values = ["" if v is None else str(v) for v in row]
                else:
                    # If this table has fewer rows than max, pad with empties
                    row_values = [""] * ncols  # type: ignore[operator]
                matrix.append(row_values)

            self.logger.trace(  # type: ignore[attr-defined]
                f"csv_table for table (header len {len(padded_header)}): {padded_header}"
            )
            self.logger.trace(f"csv_table rows: {matrix}")  # type: ignore[attr-defined]
            main_matrix.append(matrix)

        for index in range(0, max_rows + 1):
            for matrix in main_matrix:
                payload += sep.join(matrix[index]) + sep

            payload = payload[:-1]
            if index < max_rows:
                payload += "\n"

        return payload

    def __boilerplate_merge(
        self, base: list, incoming: Boilerplate, table: dict
    ) -> Boilerplate:
        """Merge table boilerplate with existing tables to handle duplicates.

        Args:
            base (list[Boilerplate]): List of existing boilerplate structures.
            incoming (Boilerplate): New boilerplate to merge.
            table (dict): Table configuration dict.

        Returns:
            Boilerplate: Merged or updated boilerplate structure.
        """
        # Structure to hold extracted header + rows for this table
        for ex_boiler in base:
            if ex_boiler.get("name", "") == incoming.get("name", ""):
                self.logger.warning(
                    f"duplicate table name '{incoming.get('name', '<unnamed>')}' found in template; try to merge"
                )
                if ex_boiler.get("header", "") == incoming.get("header", ""):
                    self.logger.debug(
                        f"merging rows for table '{incoming.get('name', '<unnamed>')}'"
                    )
                    incoming = ex_boiler
                    self.logger.debug(f"incoming: {incoming}")  # type: ignore[attr-defined]

                    base.remove(ex_boiler)
                else:
                    self.logger.error(
                        f"cannot merge table '{incoming.get('name', '<unnamed>')}' due to differing headers; skipping"
                    )
        return incoming

    def __cleanup_protect_boilerplate(self, payload_row: list, sep, multiline) -> list:
        # Cleanup rows
        for index in range(len(payload_row)):
            # Lists: support two behaviors controlled by the `multiline` flag.
            # - If `multiline` is True, emit each list item on its own line,
            #   prefixing lines with a dash ("-") and preserving newlines.
            # - If `multiline` is False, join items inline with a dash.
            if isinstance(payload_row[index], list):
                # Convert each element to str first (defensive) then join
                cleaned_items = [
                    " ".join(str(i).replace(sep, " ").strip().split())
                    for i in payload_row[index]
                ]
                if multiline:
                    # Multiline output: prefix first line with '-' and separate
                    # subsequent items with a newline+dash so the visual format
                    # matches the previous behavior while controlled by flag.
                    payload_row[index] = '"-' + "\n-".join(cleaned_items) + '"'
                else:
                    # Single-line output: join with a dash and wrap in quotes
                    payload_row[index] = "*".join(cleaned_items)
                self.logger.trace(  # type: ignore[attr-defined]
                    "warning: complex types (list) are not supported in output; converting to string"
                )
            elif isinstance(payload_row[index], dict):
                # Dicts are flattened to a single-line-ish representation
                payload_row[index] = (
                    str(payload_row[index])
                    .replace("\n", "\n-")
                    .replace("\r", " ")
                    .replace(sep, " ")
                )
                self.logger.trace(  # type: ignore[attr-defined]
                    "warning: complex types (dict) are not supported in output; converting to string"
                )
            else:
                # Primitive values: coerce to str and remove raw newlines and separator
                payload_row[index] = (
                    str(payload_row[index])
                    .replace("\n", " ")
                    .replace("\r", " ")
                    .replace(sep, " ")
                )
        return payload_row

    def __process_table(
        self, boilerplate, blob, body, sep, multiline, wildcard_keys=[]
    ) -> None:
        """Process a single table by extracting and formatting cell values.

        Args:
            boilerplate (Boilerplate): Table structure to populate with rows.
            blob (dict | list): The JSON blob to extract data from.
            body (dict): Mapping of column names to JSON paths.
            sep (str): CSV separator character.
            multiline (bool): Whether to emit list items as multiple lines.
            wildcard_keys (list): List of wildcard capture keys (default: []).
        """
        # Each element in blob is expected to be an entry we can map
        for b in blob:
            self.logger.trace(f"processing blob entry: {b}")  # type: ignore[attr-defined]
            payload_row: list[str] = []
            for entry_key, entry_path in body.items():
                finished = False

                if type(blob) is list:
                    entries = b
                    if entry_path == "$|$":
                        # for value in entries:
                        boilerplate["rows"].append(
                            self.__cleanup_protect_boilerplate(
                                [entries], sep=sep, multiline=multiline
                            )
                        )  # type: ignore[union-attr]
                        continue
                elif type(blob) is dict:
                    entries = blob[b]
                    if entry_path == "$head$":
                        payload_row.append(b)
                        continue
                    elif entry_path == "$value$":
                        payload_row.append(blob.get(b, "NULL"))
                        continue
                    else:
                        pass
                else:
                    payload_row = ["NULL"] * len(body.items())
                    continue

                for step in entry_path.split("//"):
                    self.logger.trace(f"step: {step}, entries: {entries}")  # type: ignore[attr-defined]
                    if step in entries.keys():
                        entries = entries.get(step, {})
                    elif step == "*":
                        # Wildcard step: capture all values at this level as a list
                        entries = list(entries.values())
                        self.logger.trace(f"wildcard entries: {entries}")  # type: ignore[attr-defined]
                    elif len([x for x in entries.keys() if re.match(step, x)]) > 0:
                        matched_key = [x for x in entries.keys() if re.match(step, x)][
                            0
                        ]
                        entries = entries.get(matched_key, {})
                    elif step == "$0$":
                        entries = wildcard_keys
                    else:
                        entries = None
                        break
                else:
                    finished = True

                if entries is None and not finished:
                    # Missing sub-path — log and skip the cell
                    self.logger.warning(
                        f"warning: path '{entry_path}' not found in input JSON"
                    )
                    continue
                else:
                    payload_row.append(entries)

            if len(payload_row) > 0:
                boilerplate["rows"].append(self.__cleanup_protect_boilerplate(payload_row, sep=sep, multiline=multiline))  # type: ignore[union-attr]

            # Record table dimensions
            boilerplate["ncols"] = len(boilerplate["header"])  # type: ignore[arg-type]
            boilerplate["nrows"] = len(boilerplate["rows"])  # type: ignore[arg-type]


def main(args=None):
    """Main entry point for the csv4j application.

    Args:
        args (argparse.Namespace | None): Parsed arguments object (default: None, parsed from command line).

    Returns:
        int: Exit code (0 on success).
    """
    # Allow passing a parsed args object for easier testing; otherwise parse
    # from the command-line.
    args = parse_args()
    Template(args.template).validate()
    csv4j = Csv4J(args.input, args.output, args.template, args.verbose)
    # Pass the separator and multiline flag into processing
    csv4j.process(args.sep, args.multiline)
    return 0


if __name__ == "__main__":
    # When executed directly, parse arguments and run main. We use
    # SystemExit to return the application's status code to the shell.
    parsed = parse_args()
    raise SystemExit(main(parsed))
