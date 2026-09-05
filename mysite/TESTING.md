# Testování

Z kořenové složky repozitáře spusťte:

```sh
cd mysite
../venv/bin/python manage.py test --settings=mysite.settings.test --noinput
```

Pokud prostředí `venv` ještě neexistuje, vytvořte ho pomocí `python3 -m venv venv`
v kořeni repozitáře a nainstalujte `venv/bin/python -m pip install -r mysite/requirements.txt`.

Testovací nastavení nepoužívá místní `dev.py`, `.env` ani produkční konfiguraci.
Databáze SQLite, nahrané obrázky a e-maily zůstávají v paměti; testy nepracují
s obsahem místního webu. Migrace se při přípravě testovací databáze normálně spouštějí.

## Pokrytí

- Blog a programování: publikované články, řazení, tagy, číslování, galerie,
  autoři a vykreslení stránek.
- Recepty: kategorie, tagy, řazení, kruhová navigace, náhled konceptu,
  obrázky a obsah receptu.
- Autovandry: seznam cest a dnů, navigace, validace modelů i skutečného
  redakčního formuláře, videa, mapy a převod staršího obsahu včetně revizí.
- Domovská stránka a společné části: viditelnost položek menu, patička,
  výběr webu, počítání potomků a validace obsahových bloků.
- Vyhledávání: skutečný databázový index, koncepty, stránkování, prázdné
  výsledky a escapování dotazu.
- JavaScript: preference barevného režimu, přepínání, popisky a ikony,
  změny systémového nastavení a nedostupné úložiště.

JavaScriptový test automaticky použije `chromium` nebo `google-chrome` z `PATH`
v bezhlavém režimu s dočasným profilem. Bez prohlížeče se označí jako přeskočený.
Spouští deset izolovaných scénářů nad produkčním skriptem s náhradami DOM,
`matchMedia` a `localStorage`; nejde o vizuální test vzhledu stránky.
V omezeném sandboxu může spuštění prohlížeče vyžadovat povolení.

## Vybrané testy

```sh
../venv/bin/python manage.py test recipes roadtrips --settings=mysite.settings.test
../venv/bin/python manage.py test base.test_theme --settings=mysite.settings.test
```

Kontrola souladu modelů a migrací:

```sh
../venv/bin/python manage.py makemigrations --check --dry-run --settings=mysite.settings.test
```
