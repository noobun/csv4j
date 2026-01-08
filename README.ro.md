# csv4j
[![EN](https://img.shields.io/badge/lang-en-red.svg)](README.md)


Utilitar CLI simplu pentru extragerea tabelelor din JSON și generarea reprezentărilor CSV.

## Scop
- Convertește payload-uri JSON structurate în tabele CSV mici conform unui șablon YAML. Util pentru extrageri ad-hoc de date din structuri JSON imbricate.

## Utilizare
- Rulează instrumentul din rădăcina repository-ului:

```
python3 src/csv4j.py -i <input.json> -t <template.yaml> -o <output.csv>
```

- Argumente:
  - `-i, --input`: fișierul JSON de intrare (obligatoriu)
  - `-o, --output`: fișierul CSV de ieșire (obligatoriu)
  - `-t, --template`: fișierul YAML cu șablonul (obligatoriu)
  - `-s, --sep`: caracterul separator CSV (opțional; unul dintre `,`, `|`, `;`; implicit: `,`)
  - `-ml, --multiline`: Emite celulele de tip listă pe mai multe linii; altfel listele sunt unite inline (opțional; implicit: dezactivat)

- Verbositate:
  - fără `-v`: stdout afișează INFO și niveluri superioare; jurnalul (`csv4j.log`) capturează DEBUG.
  - `-v`: stdout afișează DEBUG și niveluri superioare; jurnalul capturează TRACE.
  - `-vv`: stdout afișează TRACE și jurnalul capturează TRACE.

Exemple:

```
python3 src/csv4j.py -i tests/products.json -t tests/template.yaml -o products.csv
python3 src/csv4j.py -i tests/products.json -t tests/template.yaml -o products.csv -v
```

## Implementare (la nivel înalt)
- CLI-ul este implementat în `src/csv4j.py`.
- Un șablon YAML specifică tabelele de extras: fiecare tabel are o `path` în JSON și un `body` care mapează cheile coloanelor la căi JSON.
- Instrumentul construiește un `table_payload` cu `header` și `rows` pentru fiecare tabel, normalizează headerele și rândurile pentru o ordine deterministă și poate emite o matrice în format CSV pentru fiecare tabel.
- Logging: mesajele sunt scrise în `csv4j.log`; ieșirea pe consolă este controlată prin flag-urile de verbositate. Este implementat un nivel TRACE personalizat pentru truze de depanare detaliate.

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

## Licență
- Acest proiect este licențiat sub MIT License. Vezi fișierul `LICENSE` pentru detalii.

## Mulțumiri speciale
- https://github.com/Ovi/DummyJSON Pentru date de test JSON

## Declarație / Fără răspundere
- Acest software este furnizat "așa cum este", fără garanții de niciun fel. Autorii și contribuabilii nu sunt responsabili pentru daunele ce pot rezulta din utilizare.
