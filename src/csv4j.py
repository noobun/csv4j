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
from typing import TypedDict, Union
import time
import re
import glob
import shutil


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
        help="Input JSON file(s) (one or more). Provide multiple paths separated by space.",
        metavar="INPUT",
        required=True,
        nargs="+",
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
        help="Increase verbosity (-v for debug)",
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
        "-c",
        "--carry",
        help="Copy input files to the output parent directory when set",
        default=False,
        action="store_true",
        required=False,
    )
    parser.add_argument(
        "-ml",
        "--multiline",
        help="When set, list-type cells are emitted as multiple lines (each prefixed with '-'). Otherwise lists are joined inline.",
        action="store_true",
        required=False,
    )
    parser.add_argument(
        "-n",
        "--none",
        help="String to use when a JSON path is not found (default: empty string)",
        metavar="NONE",
        default="",
        required=False,
        type=str,
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

    def __init__(self, verbose: int = 0) -> None:
        """Initialize Csv4J processor.

        Args:
            verbose (int): Verbosity level for console output (default: 0).
        """
        # initialize or reuse a native logger.
        self.logger = logging.getLogger(__file__)
        if self.logger.handlers:
            # Reuse root logger configuration; prefer existing handlers
            self.logger.debug("Using root logger for csv4j output")
        else:
            console_handler = logging.StreamHandler(sys.stdout)
            # Map verbosity to console log level: none => INFO, -v+ => DEBUG
            if verbose >= 2:
                console_level = logging.DEBUG
            elif verbose == 1:
                console_level = logging.INFO
            else:
                console_level = logging.WARNING

            console_handler.setFormatter(
                logging.Formatter("%(levelname)-8s: %(message)s")
            )
            self.logger.addHandler(console_handler)
            self.logger.setLevel(console_level)
            self.logger.debug(
                "Logger 'csv4j' initialized (console only) with verbosity %d", verbose
            )

        self.logger.info("csv4j - lightweight CSV from json tool")

        self.input: list[dict] = []
        self.template: dict = {}
        self._customization: dict = {
            "sep": ",",
            "multiline": False,
            "none": "",
        }
        self.data: dict = {}
        # Validate that the input/template files exist and have expected ext

    def __template_is_valid(self, template: dict) -> bool:
        """Validate a template dict against the embedded JSON schema.

        Args:
            template (dict): The parsed YAML template as a dictionary.

        Returns:
            bool: True when template is valid; raises from jsonschema.validate on failure.
        """
        from jsonschema import validate

        # Validate the YAML template against the embedded JSON schema
        schema = self.structure
        tpl = template
        validate(instance=tpl, schema=schema)
        return True

    def separator(self, sep: str) -> bool:
        """Set the CSV field separator used when generating output.

        Args:
            sep (str): One of the supported separator characters: ',', '|', ';'.

        Returns:
            bool: True on success; False and logs an error when an unsupported
                separator is provided.
        """
        if sep not in [",", "|", ";"]:
            self.logger.error("sep must be one of ',', '|', or ';'")
            return False
        self._customization["sep"] = sep
        return True

    def multiline(self, multiline: bool) -> bool:
        """Enable or disable multiline rendering for list-type cells.

        When enabled, lists are emitted as multiple lines (each prefixed with
        a dash) for visual clarity. When disabled, lists are joined inline.

        Args:
            multiline (bool): True to enable multiline output, False to disable.

        Returns:
            bool: True on success; False and logs an error when the provided
                value is not a boolean.
        """
        if multiline not in [True, False]:
            self.logger.error("multiline must be a boolean value (True/False)")
            return False
        self._customization["multiline"] = multiline
        return True

    def noneplaceholder(self, placeholder: str) -> bool:
        """Set the string used when a JSON path is not found (the NONE token).

        Args:
            placeholder (str): The string to emit for missing values (e.g. "N/A").

        Returns:
            bool: True on success; False and logs an error when the provided
                placeholder is not a string.
        """
        if type(placeholder) is not str:
            self.logger.error("none value must be a string")
            return False
        self._customization["none"] = placeholder
        return True

    def customize(self, sep: str, multiline: bool, none: str = "") -> bool:
        """Customize CSV output settings.

        Args:
            sep (str): CSV separator character (,;|).
            multiline (bool): If True, list items are emitted as multiple lines.
            none (str): Value to use when a JSON path is not found. When
                omitted the current customization value is unchanged.
        """
        self.multiline(multiline)
        self.noneplaceholder(none)
        self.separator(sep)

        return True

    def load_template(self, path: Path, wildcard: bool = False) -> Union[dict, None]:
        """Load a YAML template from `path` and validate it.

        Args:
            path (Path): Path to a YAML template file (or glob when `wildcard` True).
            wildcard (bool): If True, treat `path` as a glob and allow a single match.

        Returns:
            dict | None: The loaded template dict on success, otherwise None.
        """

        if wildcard:
            matched_files = glob.glob(str(path))
            if len(matched_files) == 0:
                self.logger.error("no files matched the input pattern '%s'", path)
                return None
            elif len(matched_files) == 1:
                path = Path(matched_files[0])
            else:
                self.logger.error(
                    "multiple files matched the input pattern '%s'; please provide a single file",
                    path,
                )
                return None

        if not path.exists() or not path.is_file():
            self.logger.error(
                "template file '%s' does not exist or is not a file", path
            )
            return None

        tmp = yaml.safe_load(path.read_text(encoding="utf-8"))
        return self.loads_template(tmp)

    def loads_template(self, input: dict) -> Union[dict, None]:
        """Load and validate a template provided as a dictionary.

        Args:
            input (dict): Parsed YAML template as a dict.

        Returns:
            dict | None: The stored template dict on success, otherwise None.
        """
        if self.__template_is_valid(input):
            self.logger.debug("template YAML loaded and validated successfully")
            self.template = input
            return self.template
        else:
            return None

    def load_input(
        self, path: Path, wildcard: bool = False, carry: None | Path = None
    ) -> Union[dict, None]:
        """Load a JSON input file from `path` (supports globbing when `wildcard` True).

        Args:
            path (Path): Path (or glob) to the input JSON file.
            wildcard (bool): If True, treat `path` as a glob and allow a single match.
            carry (Path | None): Optional destination path for copying the input file.
                When provided, if `carry` is a directory the input will be copied
                into that directory preserving the input filename. If `carry` is
                a file path the file will be copied to that exact path (parent
                directories will be created as needed). Copy failures produce an
                error log and the method returns `None`.

        Returns:
            dict | None: The parsed JSON object on success, otherwise None.
        """

        if wildcard:
            matched_files = glob.glob(str(path))
            if len(matched_files) == 0:
                self.logger.error("no files matched the input pattern '%s'", path)
                return None
            elif len(matched_files) == 1:
                path = Path(matched_files[0])
            else:
                self.logger.error(
                    "multiple files matched the input pattern '%s'; please provide a single file",
                    path,
                )
                return None

        if carry is not None:
            try:
                if carry.exists() and carry.is_dir():
                    target = carry / path.name
                    shutil.copy2(path, target)
                else:
                    # treat 'carry' as a file destination
                    if not carry.exists():
                        carry.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, carry)
            except Exception as e:
                self.logger.error(
                    f"failed to copy input from {input} to {carry}! Error: {e}"
                )
                return None

        if not path.exists() or not path.is_file():
            self.logger.error("input file '%s' does not exist or is not a file", path)
            return None

        with open(path, "r", encoding="utf-8") as f:
            in_stream = json.load(f)
        return self.loads_input(in_stream, path.stem)

    def loads_input(self, input: dict, id: str) -> Union[dict, None]:
        in_stream = input
        if type(in_stream) is dict:
            self.logger.debug(  # type: ignore[attr-defined]
                f"input JSON loaded successfully as dictionary with {len(in_stream)} top-level keys"
            )
        elif type(in_stream) is list:
            in_stream = {".": in_stream}
            self.logger.debug(  # type: ignore[attr-defined]
                f"input JSON loaded successfully as list with {len(in_stream)} top-level entries"
            )
        else:
            self.logger.error("warning: input JSON is neither an object nor an array")
            return None

        self.input.append({id: in_stream})
        self.__consolidate_inputs()
        return in_stream

    def __consolidate_inputs(self) -> None:
        """Consolidate multiple loaded inputs into the internal `data` structure.

        If multiple inputs were loaded they are merged under their ids, otherwise
        the single input is promoted to `self.data` for processing.
        """
        self.data = {}
        if len(self.input) > 1:
            for i in self.input:
                for k, v in i.items():
                    self.data[k] = v
        else:
            tmp = self.input[0]
            self.data = tmp[list(tmp.keys())[0]]

    def writecsv(self, path: Path) -> str:
        """Write the generated CSV payload to `path` and return the payload.

        Args:
            path (Path): Destination path for the CSV output.

        Returns:
            str: The CSV payload that was written.
        """
        with open(path, "w", encoding="utf-8") as out_stream:
            payload = self.getcsv()
            out_stream.write(payload)
            out_stream.close()
            self.logger.info(f"output written to '{path}'")
        return payload

    def getcsv(self) -> str:
        """Return the generated CSV payload as a string using current customization.

        Returns:
            str: The CSV payload.
        """
        return self.__process(
            sep=self._customization["sep"],
            multiline=self._customization["multiline"],
            none=self._customization["none"],
        )

    def __process(self, sep: str = ",", multiline: bool = False, none: str = "") -> str:
        """Process JSON input using the template and write CSV output.

        Args:
            sep (str): CSV separator character (default: ',').
            multiline (bool): If True, list items are emitted as multiple lines.
                            If False, lists are joined inline (default: False).
        """
        start = time.perf_counter()

        # Accumulate per-table intermediate payloads and track max dimensions
        table_payload = []  # type: ignore[var-annotated]
        max_rows = -1
        max_cols = -1

        for table in self.template.get("tables", []):
            # Start blob at root of the JSON input copy so we can drill down
            blob = {**self.data}  # type: ignore[index]

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
            # for blob in recursive_results:
            #     if blob is None:
            #         # Missing path — skip this table and warn user
            #         self.logger.warning(
            #             f"warning: path '{path}' not found in input JSON"
            #         )
            #         continue
            # else:
            boilerplate = self.__boilerplate_merge(table_payload, boilerplate, table)
            self.__process_table(
                boilerplate=boilerplate,
                blob=recursive_results,
                body=body,
                sep=sep,
                multiline=multiline,
                none=none,
            )  # type: ignore[union-attr]

            max_cols = max(max_cols, boilerplate["ncols"])  # type: ignore[assignment]
            max_rows = max(max_rows, boilerplate["nrows"])  # type: ignore[assignment]

            table_payload.append(boilerplate)
            self.logger.debug(f"boilerplate: {boilerplate}")  # type: ignore[attr-defined]
            self.logger.info(f"{boilerplate['name']} table done.")

        self.logger.debug(f"max rows: {max_rows}, max cols: {max_cols}")

        if len(self.template.get("pipes", {})) > 0:
            self.logger.info("starting pipes processing")
            for pipe_k, pipe_v in self.template.get("pipes", {}).items():
                self.logger.info(f"processing pipe: {pipe_k}")
                dump = set(self.__recursive_process_path(blob, pipe_v))
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

        # code to measure
        end = time.perf_counter()

        elapsed = end - start
        self.logger.info(f"csv4j processing completed in {elapsed:.4f} seconds")

        return payload

    def __recursive_process_path(self, blob, path, wildcard={}):
        """Recursively process a JSON path with wildcard support.

        Args:
            blob (dict): The JSON object/dict to process.
            path (str): The path string with steps separated by '//'.
            wildcard (dict): Dictionary of wildcard captures (default: {}).

        Returns:
            list[dict]: List of processed blob dictionaries.
        """

        def is_nested(d):
            """Check if any value in the dictionary is itself a dictionary"""
            return any(isinstance(v, dict) for v in d.values())

        # Recursively process a path within a blob
        payload = []
        self.logger.debug(
            f"resursive at start: {blob}, path: {path}, wildcard: {wildcard}"
        )
        for step in path.split("//"):
            self.logger.debug(
                f"resursive at step: {blob}, path: {path}, wildcard: {wildcard}"
            )
            path = "//".join(path.split("//")[1:])
            if step in blob:
                blob = blob[step]
            elif step == "*":
                if type(blob) is list:
                    for item in blob:
                        payload += self.__recursive_process_path(
                            item, path, {**wildcard}
                        )
                elif type(blob) is dict:
                    # Wildcard step: capture all values at this level as a list
                    for k, b in blob.items():
                        # wildcard[f"${len(wildcard.keys())}$"] = k
                        payload += self.__recursive_process_path(
                            b, path, {**wildcard, f"${len(wildcard.keys())}$": k}
                        )
                else:
                    pass
                blob = None
                break
            elif step == "" or step is None:
                break
            else:
                blob = None
                continue

        # Append the final blob if not None
        if blob is not None:
            if type(blob) is dict:
                # payload.append(blob)
                for k, v in blob.items():
                    payload.append({k: v})
            elif type(blob) is list:
                for b in blob:
                    payload.append(b)
            else:
                payload.append(blob)

        for p in payload:
            for k, v in wildcard.items():
                if type(p) is dict:
                    if not is_nested(p):
                        p[k] = v
                    elif is_nested(p) and len(p.keys()) == 1:
                        # unwrap single-key nested dicts
                        head = list(p.keys())[0]
                        if type(p[head]) is dict:
                            p[head][k] = v

        self.logger.debug(  # type: ignore[attr-defined]
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

            self.logger.debug(  # type: ignore[attr-defined]
                f"csv_table for table (header len {len(padded_header)}): {padded_header}"
            )
            self.logger.debug(f"csv_table rows: {matrix}")  # type: ignore[attr-defined]
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
        """Cleanup and coerce a row payload to safe CSV-friendly strings.

        Args:
            payload_row (list): List of raw cell values.
            sep (str): The CSV separator to avoid in output.
            multiline (bool): Whether multiline formatting is active.

        Returns:
            list: The cleaned/serialized row values.
        """
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
                self.logger.debug(  # type: ignore[attr-defined]
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
                self.logger.debug(  # type: ignore[attr-defined]
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
        self, boilerplate, blob, body, sep, multiline, none, wildcard_keys=[]
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

        def is_nested(d):
            """Check if any value in the dictionary is itself a dictionary"""
            return any(isinstance(v, dict) for v in d.values())

        # Each element in blob is expected to be an entry we can map
        for b in blob:
            self.logger.debug(f"processing blob entry: {b}")  # type: ignore[attr-defined]
            payload_row: list[str] = []
            for entry_key, entry_path in body.items():
                finished = False
                if (
                    type(b) is not list and type(b) is not dict
                ):  # only for list entry with no key
                    if entry_path == "$|$":
                        # for value in entries:
                        boilerplate["rows"].append(
                            self.__cleanup_protect_boilerplate(
                                [b], sep=sep, multiline=multiline
                            )
                        )  # type: ignore[union-attr]
                        continue
                elif type(b) is dict:
                    if (not is_nested(b) and len(b.keys()) == 1) or (
                        is_nested(b) and len(b.keys()) == 1
                    ):
                        # unwrap single-key nested dicts
                        head = list(b.keys())[0]
                        if entry_path == "$head$":
                            payload_row.append(head)
                            continue
                        elif entry_path == "$value$":
                            payload_row.append(b.get(head, "NULL"))
                            continue
                        entries = b.get(head, {})
                    else:
                        entries = b
                else:
                    payload_row = ["NULL"] * len(body.items())
                    continue

                for step in entry_path.split("//"):
                    self.logger.debug(f"step: {step}, entries: {entries}")  # type: ignore[attr-defined]
                    if step in entries.keys():
                        entries = entries.get(step, {})
                    elif step == "*":
                        # Wildcard step: capture all values at this level as a list
                        entries = list(entries.values())
                        self.logger.debug(f"wildcard entries: {entries}")  # type: ignore[attr-defined]
                    elif len([x for x in entries.keys() if re.match(step, x)]) > 0:
                        matched_key = [x for x in entries.keys() if re.match(step, x)][
                            0
                        ]
                        entries = entries.get(matched_key, {})
                    # elif step == "$0$":
                    #     entries = wildcard_keys
                    else:
                        entries = None
                        break
                else:
                    finished = True

                if entries is None and not finished:
                    # Missing sub-path — log and substitute the configured NONE
                    self.logger.warning(
                        f"warning: path '{entry_path}' not found in input JSON"
                    )
                    entries = none

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
    c4j = Csv4J(args.verbose)
    # Pass the separator, multiline flag and missing-value token into processing
    c4j.customize(args.sep, args.multiline, args.none)
    # Load template
    tpl = c4j.load_template(args.template)
    if tpl is None:
        return 1
    # Load one or more input JSON files
    for inpath in args.input:
        inp = c4j.load_input(
            inpath, wildcard=False, carry=args.output.parent if args.carry else None
        )
        if inp is None:
            return 2
    # Write output CSV
    dump = c4j.writecsv(args.output)
    if dump is None:
        return 3
    return 0


if __name__ == "__main__":
    # When executed directly, parse arguments and run main. We use
    # SystemExit to return the application's status code to the shell.
    parsed = parse_args()
    raise SystemExit(main(parsed))
