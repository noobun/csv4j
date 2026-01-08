# csv4j
[![ro](https://img.shields.io/badge/lang-ro-red.svg)](README.ro.md)


Lightweight CLI utility to extract tables from JSON and emit CSV representations.

## Purpose
- Convert structured JSON payloads into small CSV tables according to a YAML template. Useful for ad-hoc data extraction from nested JSON structures.

## Usage
- Run the tool from the repository root:

```
python3 src/csv4j.py -i <input.json> -t <template.yaml> -o <output.csv>
```

- Arguments:
  - `-i, --input`: Input JSON file (required)
  - `-o, --output`: Output CSV file (required)
  - `-t, --template`: Template YAML file (required)
  - `-s, --sep`: CSV separator character (optional; one of `,`, `|`, `;`; default: `,`)
  - `-s, --sep`: CSV separator character (optional; one of `,`, `|`, `;`; default: `,`)
  - `-ml, --multiline`: Emit list-type cells as multiple lines when present; otherwise lists are joined inline (optional; default: off)

- Verbosity:
  - no `-v`: stdout shows INFO and higher; logfile (`csv4j.log`) captures DEBUG.
  - `-v`: stdout shows DEBUG and higher; logfile captures TRACE and above.
  - `-vv`: stdout shows TRACE and logfile captures TRACE.

Examples:

```
python3 src/csv4j.py -i tests/products.json -t tests/template.yaml -o products.csv
python3 src/csv4j.py -i tests/products.json -t tests/template.yaml -o products.csv -v
```

## Implementation (high level)
- The CLI is implemented in `src/csv4j.py`.
- A YAML template specifies the tables to extract: each table has a `path` into the JSON and a `body` mapping of column keys to JSON paths.
- The tool builds a `table_payload` with `header` and `rows` for each table, normalizes headers and rows to deterministic ordering, and can emit a CSV-shaped matrix for each table.
- Logging: messages go to `csv4j.log`; console output is controlled by verbosity flags. A custom TRACE level is implemented for very verbose traces.

## Table Merge Behavior

When multiple template entries target the same table name (id) and produce the same CSV header, the tool merges those results into a single CSV table by appending rows rather than emitting duplicate tables. This keeps output compact and avoids duplicated CSV files when different template scopes produce homogeneous rows for the same logical table.

### Example

YAML snippets (two template entries that target the same table):##

```
tables:
  - path: items.partA
    name: "inventory"
    body:
      id: sku
      name: title
      qty: quantity

  - path: items.partB
    name: "inventory"
    body:
      id: sku
      name: title
      qty: quantity
```

-   Resulting CSV header: `id,name,qty`
-   Resulting CSV rows:rows extracted from `items.partA` followed by rows from `items.partB` (same header so merged into one `inventory.csv` table).

-   Notes: If headers differ (different set or ordering of columns) the tool will treat them as separate tables to avoid ambiguous column alignment.

## License
- This project is licensed under the MIT License. See the `LICENSE` file for details.

## Special Thanks
- https://github.com/Ovi/DummyJSON For json test data

## Disclaimer / No Liability
- This software is provided "as is", without warranty of any kind. The authors and contributors are not liable for any damages arising from use of this software.
