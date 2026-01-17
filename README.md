# csv4j
[![ro](https://img.shields.io/badge/lang-ro-red.svg)](README.ro.md)


Lightweight CLI utility to extract tables from JSON and emit CSV representations.

## Purpose
- Convert structured JSON payloads into small CSV tables according to a YAML template. Useful for ad-hoc data extraction from nested JSON structures.

## Table of Contents

- [Usage](#usage)
- [Implementation (high level)](#implementation-high-level)
- [Table Merge Behavior](#table-merge-behavior)
- [Template syntax and special tokens](#template-syntax-and-special-tokens)
- [Small examples (quick, runnable snippets)](#small-examples-quick-runnable-snippets)
- [Using as a wheel or from Python](#using-as-a-wheel-or-from-python)
- [License](#license)
- [Special Thanks](#special-thanks)
- [Disclaimer / No Liability](#disclaimer--no-liability)

## Usage
- Run the tool from the repository root:

```
python3 src/csv4j.py -i <input.json> -t <template.yaml> -o <output.csv>
```

- Arguments:
  - `-i, --input`: Input JSON file (required)
  - `-o, --output`: Output CSV file (required)
  - `-t, --template`: Template YAML file (required)
  - `-n, --none`: String to use when a JSON path is not found (optional; default: empty string)
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

## Template syntax and special tokens

Templates use `tables:` entries where each table defines a `path` (steps separated by `//`), an optional `name`, and a `body` mapping of CSV header → JSON path.

- Path notes:
  - Steps are separated with `//` to drill into nested objects/arrays (example: `catalog//classes//III//childs`).
  - Use `*` as a wildcard step to capture keys at that level — captured values are injected as `$0`, `$1`, ... into extracted blobs.
  - Use `.` to refer to the current root blob.

- Body mapping special tokens and examples (see `tests/payloads`):
  - `$head$`: when a blob entry is a single-key mapping, `$head$` yields the key name. (example: [tests/payloads/payload1/template.yaml](tests/payloads/payload1/template.yaml#L1))
  - `$value$`: when a blob entry is a single-key mapping, `$value$` yields that key's value.
  - `$|$`: used when the table `path` points at a list of primitive values; `$|$` emits the primitive as the cell (see [tests/payloads/payload9/template.yaml](tests/payloads/payload9/template.yaml#L1)).
  - `$0`, `$1`, ...: values captured by `*` wildcards in the `path` are injected as `$0`, `$1`, etc., and can be referenced in `body` (see [tests/payloads/payload7/template.yaml](tests/payloads/payload7/template.yaml#L1)).
  - Regex/partial matches in `body` steps are supported — a step in `body` may match a key using `re.match` (see [tests/payloads/payload10/template.yaml](tests/payloads/payload10/template.yaml#L1)).

- Pipes:
  - A `pipes:` mapping at top-level can extract single values (by JSON path) and append them as extra one-column tables aligned to the main table height (see [tests/payloads/payload8/template.yaml](tests/payloads/payload8/template.yaml#L1)).

Example snippet (wildcard + head + capture):

```yaml
tables:
  - path: catalog//classes//*//childs
    name: "childs db"
    body:
      class: $0$
      name: $head$
      grade.math: math
```

This will capture the `*` key at the `classes` level into `$0` and the single-key child entries' keys into `$head$`, producing columns `class,name,grade.math`.

### Small examples (quick, runnable snippets)

- Example: single-key mappings with `$head$` / `$value$`

template.yaml
```yaml
tables:
  - path: servers//cpu
    name: cpu
    body:
      core_name: $head$
      core_value: $value$
```

input.json
```json
{
  "servers": { "cpu": { "coreA": 10, "coreB": 20 } }
}
```

Command:
```
python3 src/csv4j.py -i input.json -t template.yaml -o out.csv
```

- Example: list-of-primitives with `$|$`

template.yaml
```yaml
tables:
  - path: tags
    name: tags
    body:
      tag: $|$
```

input.json
```json
{ "tags": ["a","b","c"] }
```

Command produces a CSV with each tag on its own row.

- Example: wildcard capture into `$0` / `$1` and using a child `$head$`

template.yaml
```yaml
tables:
  - path: projects//*//tasks
    name: tasks
    body:
      project: $0$
      task: $head$
      status: state
```

input.json
```json
{
  "projects": { "p1": { "tasks": { "t1": {"state":"ok"} } }, "p2": { "tasks": { "t2": {"state":"ko"} } } }
}
```

Command will create rows with `project,task,status` such as `p1,t1,ok`.

- Example: regex/partial match step in `body`

template.yaml
```yaml
tables:
  - path: catalog//classes
    name: classes
    body:
      class_name: "cla.*"
```

This matches keys starting with `cla` using the internal `re.match` behavior and extracts their values.

- Example: pipes

template.yaml
```yaml
tables:
  - path: records
    name: records
    body:
      id: id
pipes:
  run_at: timestamp
```

`pipes.run_at` will be emitted as a one-column table aligned to the main tables' row count.

## Using as a wheel or from Python

You can install `csv4j` from a built wheel and use it as a regular Python package, or import it directly from the repository.

- Install from a wheel file (local path):

```
pip install /path/to/csv4j-<version>-py3-none-any.whl
```

- Install from the repository (editable install for development):

```
pip install -e .
```

- Import and use in your Python scripts:

```python
from pathlib import Path
from csv4j import Csv4J

# Create a processor (verbose is optional)
c = Csv4J(verbose=1)

# Optional: set CSV separator and multiline behavior
c.customize(sep=",", multiline=False)

# Load a YAML template and a JSON input (both return dict or None on error)
tpl = c.load_template(Path("template.yaml"))
if tpl is None:
  raise RuntimeError("failed to load template")

inp = c.load_input(Path("input.json"))
if inp is None:
  raise RuntimeError("failed to load input JSON")

# Get CSV as a string
csv_text = c.getcsv()

# Or write directly to a file
c.writecsv(Path("output.csv"))
```

Notes:
- `Csv4J(verbose: int = 0)` constructs the processor; pass `verbose=1` for `DEBUG`, `verbose=2` for `TRACE` on stdout.
- Use `c.customize(sep, multiline)` to control separator (`,`, `|`, `;`) and whether lists are emitted as multiple lines.
- `load_template` / `loads_template` and `load_input` / `loads_input` accept `pathlib.Path` or dicts; when `wildcard=True` the path supports globbing.
- Use `getcsv()` to obtain the CSV payload as a string, or `writecsv(Path(...))` to write it to disk.
 - `c.customize(sep, multiline, none)` also accepts a `none` string to use when a JSON path is not found (for example: `c.customize(sep=",", multiline=False, none="N/A")`).

## License
- This project is licensed under the MIT License. See the `LICENSE` file for details.

## Special Thanks
- https://github.com/Ovi/DummyJSON For json test data

## Disclaimer / No Liability
- This software is provided "as is", without warranty of any kind. The authors and contributors are not liable for any damages arising from use of this software.
