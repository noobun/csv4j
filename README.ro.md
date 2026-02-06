# csv4j
[![EN](https://img.shields.io/badge/lang-en-red.svg)](README.md)


Utilitar CLI simplu pentru extragerea tabelelor din JSON și generarea reprezentărilor CSV.

## Scop
- Convertește payload-uri JSON structurate în tabele CSV mici conform unui șablon YAML. Util pentru extrageri ad-hoc de date din structuri JSON imbricate.

## Cuprins

- [Utilizare](#utilizare)
- [Implementare (la nivel înalt)](#implementare-la-nivel-%C3%AEnalt)
- [Comportament la unire a tabelelor](#comportament-la-unire-a-tabelelor)
- [Sintaxa șabloanelor și token-uri speciale](#sintaxa-%C8%99abloanelor-%C8%99i-token-uri-speciale)
- [Exemple mici (snippet-uri rapide și rulabile)](#exemple-mici-snippet-uri-rapide-%C8%99i-rulabile)
- [Utilizare ca wheel sau din Python](#utilizare-ca-wheel-sau-din-python)
- [Licență](#licen%C8%9B%C4%83)
- [Mulțumiri speciale](#mul%C8%9Bumiri-speciale)
- [Declarație / Fără răspundere](#declara%C8%9Bie--f%C4%83r%C4%83-r%C4%83spundere)

## Utilizare
- Rulează instrumentul din rădăcina repository-ului:

```
python3 src/csv4j.py -i <input.json> -t <template.yaml> -o <output.csv>
```

- Argumente:
  - `-i, --input`: fișierul JSON de intrare (unul sau mai multe căi separate prin spațiu) (obligatoriu)
  - `-o, --output`: fișierul CSV de ieșire (obligatoriu)
  - `-c, --carry`: copiază fișierul/fișierele de intrare în directorul părinte al fișierului de ieșire atunci când este setat (opțional)
  - `-t, --template`: fișierul YAML cu șablonul (obligatoriu)
  - `-s, --sep`: caracterul separator CSV (opțional; unul dintre `,`, `|`, `;`; implicit: `,`)
  - `-ml, --multiline`: Emite celulele de tip listă pe mai multe linii; altfel listele sunt unite inline (opțional; implicit: dezactivat)
  - `-n, --none`: șir folosit când o cale JSON nu este găsită (opțional; implicit: șir gol)

- Verbositate:
 - Verbositate (doar consolă):
  - fără `-v`: stdout afișează INFO și niveluri superioare.
  - `-v`: stdout afișează DEBUG și niveluri superioare.
  - `-v` sau mai mult: stdout afișează DEBUG și niveluri superioare.

Exemple:

```
python3 src/csv4j.py -i tests/products.json -t tests/template.yaml -o products.csv
python3 src/csv4j.py -i tests/a.json tests/b.json -t tests/template.yaml -o products.csv -v
python3 src/csv4j.py -i tests/products.json -t tests/template.yaml -o products.csv -c
```

## Implementare (la nivel înalt)
- CLI-ul este implementat în `src/csv4j.py`.
- Un șablon YAML specifică tabelele de extras: fiecare tabel are o `path` în JSON și un `body` care mapează cheile coloanelor la căi JSON.
- Instrumentul construiește un `table_payload` cu `header` și `rows` pentru fiecare tabel, normalizează headerele și rândurile pentru o ordine deterministă și poate emite o matrice în format CSV pentru fiecare tabel.
- Ieșirea pe consolă este controlată prin flag-urile de verbositate; instrumentul nu scrie un jurnal în fișier.

## Comportament la unire a tabelelor

Când mai multe intrări din șablon vizează același nume de tabel (id) și produc același header CSV, instrumentul unește rezultatele într-un singur tabel CSV prin concatenarea rândurilor în loc să emită tabele duplicate. Aceasta păstrează ieșirea compactă și evită fișiere CSV duplicate când scope-urile diferite produc rânduri omogene pentru același tabel logic.

### Exemplu

Fragmente YAML (două intrări din șablon care vizează același tabel):

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

-   Header-ul CSV rezultat: `id,name,qty`
-   Rândurile CSV rezultate: rândurile extrase din `items.partA` urmate de cele din `items.partB` (same header, deci se unesc într-un singur tabel `inventory`).

-   Observații: Dacă headerele diferă (set diferit de coloane sau ordini diferite) instrumentul va trata tabelele ca separate pentru a evita ambiguitatea alinierii coloanelor.

## Sintaxa șabloanelor și token-uri speciale

Șabloanele folosesc `tables:` unde fiecare intrare definește un `path` (pași separați prin `//`), un `name` opțional și un `body` care mapează antetul CSV → cale JSON.

- Observații despre `path`:
  - Pașii se separă cu `//` pentru a coborî în obiecte/array-uri imbricate (ex: `catalog//classes//III//childs`).
  - Folosește `*` ca pas wildcard pentru a captura chei la acel nivel — valorile capturate sunt injectate ca `$0`, `$1`, ... în blob-urile extrase.
  - Folosește `.` pentru a se referi la blob-ul rădăcină curent.

- Token-uri speciale în `body` și exemple (vezi `tests/payloads`):
  - `$head$`: când o intrare blob este un obiect cu o singură cheie, `$head$` returnează numele acelei chei. (exemplu: [tests/payloads/payload1/template.yaml](tests/payloads/payload1/template.yaml#L1))
  - `$value$`: când o intrare blob este un obiect cu o singură cheie, `$value$` returnează valoarea acelei chei.
  - `$|$`: folosit când `path` indică o listă de valori primitive; `$|$` emite valoarea primitivă ca celulă (vezi [tests/payloads/payload9/template.yaml](tests/payloads/payload9/template.yaml#L1)).
  - `$0`, `$1`, ...: valorile capturate de `*` în `path` sunt injectate ca `$0`, `$1`, etc., și pot fi referite în `body` (vezi [tests/payloads/payload7/template.yaml](tests/payloads/payload7/template.yaml#L1)).
  - Pot fi folosite potriviri regex/parțiale în pașii din `body` — un pas poate potrivi cheia cu `re.match` (vezi [tests/payloads/payload10/template.yaml](tests/payloads/payload10/template.yaml#L1)).

- Pipes:
  - Un mapping `pipes:` la nivel înalt poate extrage valori unice (prin cale JSON) și le adaugă ca tabele cu o singură coloană, aliniate la înălțimea principală (vezi [tests/payloads/payload8/template.yaml](tests/payloads/payload8/template.yaml#L1)).

Exemplu (wildcard + head + captură):

```yaml
tables:
  - path: catalog//classes//*//childs
    name: "childs db"
    body:
      class: $0$
      name: $head$
      grade.math: math
```

Acest șablon capturează cheia `*` la nivelul `classes` în `$0` și cheile intrărilor cu o singură cheie în `$head$`, rezultând coloanele `class,name,grade.math`.

### Exemple mici (snippet-uri rapide și rulabile)

- Exemplu: mapping-uri cu o singură cheie folosind `$head$` / `$value$`

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

Comandă:
```
python3 src/csv4j.py -i input.json -t template.yaml -o out.csv
```

- Exemplu: listă de primitive cu `$|$`

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

Comanda va produce un CSV cu fiecare tag pe rândul său.

- Exemplu: captură wildcard în `$0` / `$1` și folosirea `$head$` pentru copil

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

Comanda va crea rânduri cu `project,task,status` ca `p1,t1,ok`.

- Exemplu: potrivire regex/parțială în pașii `body`

template.yaml
```yaml
tables:
  - path: catalog//classes
    name: classes
    body:
      class_name: "cla.*"
```

Aceasta potrivește cheile care încep cu `cla` folosind `re.match` intern și extrage valorile lor.

- Exemplu: pipes

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

`pipes.run_at` va fi emis ca un tabel cu o singură coloană aliniat la numărul de rânduri ale tabelului principal.

## Utilizare ca wheel sau din Python

Poți instala `csv4j` dintr-un fișier wheel și folosi pachetul în mod normal în Python, sau îl poți importa direct din repository.

- Instalare dintr-un fișier wheel (cale locală):

```
pip install /cale/catre/csv4j-<versiune>-py3-none-any.whl
```

- Instalare din repository (pentru dezvoltare):

```
pip install -e .
```

- Import și utilizare în scripturi Python:

```python
from pathlib import Path
from csv4j import Csv4J

# Crează procesorul (verbose este opțional)
c = Csv4J(verbose=1)

# Opțional: setează separatorul CSV și comportamentul multiline (apel într-o singură metodă)
c.customize(sep=",", multiline=False)

# Alternativă: setează opțiunile individual folosind metode dedicate
# (util când vrei să modifici doar o setare)
c.separator("|")         # setează separatorul CSV la '|'
c.multiline(True)         # activează afișarea multiline pentru liste
c.noneplaceholder("N/A") # șir folosit pentru valori lipsă

# Încarcă un șablon YAML și un JSON de intrare (ambele întorc dict sau None la eroare)
tpl = c.load_template(Path("template.yaml"))
if tpl is None:
  raise RuntimeError("încărcare șablon eșuată")

inp = c.load_input(Path("input.json"))
if inp is None:
  raise RuntimeError("încărcare JSON de intrare eșuată")

# Obține CSV ca string
csv_text = c.getcsv()

# Sau scrie direct în fișier
c.writecsv(Path("output.csv"))
```

Observații:
- `Csv4J(verbose: int = 0)` construiește procesorul; folosește `verbose=1` pentru `DEBUG`, `verbose=2` pentru `TRACE` pe stdout.
 - `Csv4J(verbose: int = 0)` construiește procesorul; folosește `verbose=1` (sau `-v`) pentru `DEBUG` pe stdout.
- Folosește `c.customize(sep, multiline)` pentru a controla separatorul (`,`, `|`, `;`) și dacă listele sunt emise pe mai multe linii.
- `load_template` / `loads_template` și `load_input` / `loads_input` acceptă `pathlib.Path` sau dict-uri; când `wildcard=True` calea suportă globbing.
- Folosește `getcsv()` pentru a obține payload-ul CSV ca string sau `writecsv(Path(...))` pentru a-l scrie pe disc.
 - `c.customize(sep, multiline, none)` acceptă și parametrul `none` pentru șirul folosit când o cale JSON lipsește (exemplu: `c.customize(sep=",", multiline=False, none="N/A")`).

## Licență
- Acest proiect este licențiat sub MIT License. Vezi fișierul `LICENSE` pentru detalii.

## Mulțumiri speciale
- https://github.com/Ovi/DummyJSON Pentru date de test JSON

## Declarație / Fără răspundere
- Acest software este furnizat "așa cum este", fără garanții de niciun fel. Autorii și contribuabilii nu sunt responsabili pentru daunele ce pot rezulta din utilizare.
