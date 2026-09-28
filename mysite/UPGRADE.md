# Upgrade na Wagtail 7.4 LTS a Django 5.2 LTS

Připraveno 28. 9. 2026: Wagtail 7.4.3, Django 5.2.17, Python 3.11.10.
`requirements.txt` obsahuje přesné verze všech ověřených závislostí včetně
Gunicornu. `requirements.in` obsahuje přímé závislosti a povolené řady verzí;
pro nasazení používejte `requirements.txt`.

Produkce na Roští používá Python 3.13.13 a Gunicorn 26.2.0. Pin Gunicornu byl
po zjištění produkčního stavu upraven na 26.2.0, aby nasazení nesnižovalo jeho
verzi. Python 3.13 je podporovaný Django 5.2 i Wagtail 7.4; před přepnutím
ověřte závislosti a aplikaci také v novém produkčním prostředí na tomto Pythonu.
Lokálně s Gunicornem 26.2.0 prošlo `pip check`, ověření konfigurace a skutečné
spuštění serveru s HTTP 200 pro veřejnou stránku i přihlášení do administrace.

## Místní prostředí

Z kořene repozitáře:

```sh
source venv/bin/activate
cd mysite
python manage.py runserver
```

Běžný `venv` je aktualizovaný na ověřené závislosti. Standardní vývojové
nastavení `mysite.settings.dev` používá `mysite/db.sqlite3` a `mysite/media/`.
Při trvalém přepnutí se převzala ověřená náhledová databáze včetně dvou nových
revizí autovandru a doplnilo se 40 nových souborů médií. Databáze má po přepnutí
35 stránek, 484 revizí a všech 298 migrací aplikovaných.

Po přepnutí prošlo všech 153 testů v běžném `venv`, kontroly závislostí a migrací
i ověření veřejných stránek, vyhledávání a administrace nad běžnou dev databází.
Obsah stránek, revize a údaje o médiích se shodují se zálohou náhledu.

Adresář `.upgrade/` uchovává oddělené prostředí a kopie z původního náhledu;
další běžný vývoj používá standardní cesty výše. `.upgrade/` není součástí nasazení.

Záloha těsně před trvalým přepnutím je v
`.upgrade-backups/dev-switch-20260928T170521Z/`. Obsahuje původní i náhledovou
databázi, oba archivy médií a seznam původních balíčků `original-pip-freeze.txt`.

Záloha před upgradem je v `.upgrade-backups/20260928T152850Z/`:

- `db.sqlite3`: konzistentní záloha původní databáze;
- `source.tar.gz`: zdrojové soubory sledované Gitem;
- `media.tar.gz`: původní nahrané soubory;
- `local-settings.tar.gz`: místní nastavení, která byla v projektu přítomná;
- `requirements.txt`, `pip-freeze.txt`, `baseline.json`: původní závislosti
  a identifikace výchozího stavu.

Záloha není v Gitu a obsahuje soukromá data. Je uložená se souborovými oprávněními
omezenými na vlastníka. Před produkčním nasazením bude potřeba nová záloha produkce.

## Změny projektu

- Nové, vzájemně kompatibilní závislosti jsou připnuté v `requirements.txt`.
- Vlastní videoblok podporuje nedokončený koncept i autosave. Při publikování
  dál vyžaduje video; neplatné typy souborů odmítá i při ukládání konceptu.
- Limit počtu polí formuláře je 10 000, podle doporučení Wagtailu pro rozsáhlé
  StreamField formuláře.
- Testy vyhledávání zpracují transakční callbacky pro vytvoření indexu.
- Nové migrace již nejsou ignorované Gitem. Vlastní modely při tomto upgradu
  nové migrační soubory nevyžadují; změny schématu dodává Wagtail.

## Ověření

Přechod byl ověřen přes Django 5.1.15 a 5.2.17 a následně Wagtail 6.4.2,
7.0.9, 7.1.3, 7.2.3, 7.3.4 a 7.4.3. Kontroly zahrnovaly závislosti, systémové
kontroly Djanga, migrace kopie databáze, soulad modelů s migracemi a aplikační testy.
Pro mezikroky se test prohlížeče prováděl samostatně kvůli omezením sandboxu.

Byl také ověřen přímý přechod z původní databáze na cílové závislosti jedním
`migrate`. Obsah vlastních tabulek, struktura a stav stránek, 482 revizí, tagy
a odkazy na 61 obrázků se shodovaly s výchozím stavem. SQLite kontrola integrity
i cizích klíčů prošla u postupně i přímo migrované kopie.

Na kopii reálných dat prošlo ověření 31 veřejných stránek, editačních formulářů
deseti typů stránek, hlavních obrazovek administrace a vyhledávání. Prošlo také
`collectstatic` s produkčním manifestem a `update_index` s 96 indexovanými objekty.
Závěrečná sada všech 153 testů včetně prohlížeče prošla bez přeskočených testů.

Závěrečné testy z kořene repozitáře:

```sh
cd mysite
../venv/bin/python manage.py test --settings=mysite.settings.test --noinput
../venv/bin/python manage.py makemigrations --check --dry-run --settings=mysite.settings.test
../venv/bin/python -m pip check
```

Automatické kontroly nenahrazují prohlédnutí vzhledu administrace a médií
v prohlížeči. Před nasazením projděte lokální náhled a uložte zkušební koncept
receptu a autovandru.

## Nasazení na klasickou Aplikaci Roští

Nejdříve přes SSH ověřte skutečnou verzi Pythonu, cestu k `manage.py`, databázi,
`MEDIA_ROOT`, `STATIC_ROOT`, produkční nastavení a konfiguraci Supervisoru.
Produkční cesty nejsou v repozitáři doložené; následující příklady předpokládají
`/srv/app/manage.py` a standardní proces `app`. Přizpůsobte je skutečnému stavu.

1. Zaznamenejte původní commit, verze závislostí a konfiguraci Supervisoru.
   Zálohujte média a nastavení. Připravte nové virtuální prostředí na produkčním Pythonu 3.13
   na jeho konečné cestě, například `/srv/venv-wagtail74`, a nainstalujte do něj
   nové `requirements.txt`. Prostředí po vytvoření nepřesouvejte.
2. Připravte krátkou odstávku a pozastavte úpravy obsahu. Zastavte aplikaci
   pomocí `supervisorctl stop app`; případné další procesy zapisující do databáze
   musí být také zastavené. Udělejte čerstvou konzistentní zálohu databáze
   a případně snapshot aplikace. Externí databáze vyžaduje vlastní zálohu.
3. Nasaďte připravený kód včetně migračních souborů. Zachovejte produkční databázi,
   média, `.env` a `mysite/settings/local.py`.
4. Spusťte kontroly a migrace novým Pythonem. Každý příkaz musí úspěšně skončit,
   než pokračujete dalším:

```sh
cd /srv/app
/srv/venv-wagtail74/bin/python manage.py check --settings=mysite.settings.production
/srv/venv-wagtail74/bin/python manage.py migrate --plan --settings=mysite.settings.production
/srv/venv-wagtail74/bin/python manage.py migrate --noinput --settings=mysite.settings.production
/srv/venv-wagtail74/bin/python manage.py collectstatic --noinput --settings=mysite.settings.production
/srv/venv-wagtail74/bin/python manage.py update_index --settings=mysite.settings.production
```

5. Upravte příkaz Supervisoru na nový Gunicorn, při zachování ostatních
   produkčních argumentů, pracovního adresáře a proměnných prostředí.
   Načtěte změnu pomocí `supervisorctl reread` a `supervisorctl update`;
   ověřte `supervisorctl status` a podle stavu spusťte `supervisorctl start app`.
6. Zkontrolujte logy, veřejné stránky, média, přihlášení, koncept, autosave,
   publikování a vyhledávání. Po úspěšné kontrole obnovte úpravy obsahu.

V produkci se nespouští `makemigrations`. Pro tento projekt byl přímý přechod
databáze ověřen; jednotlivá přechodná vydání se na produkci nemusí instalovat.
Tuto zkoušku je vhodné zopakovat s čerstvou produkční zálohou, pokud se před
nasazením změní schéma nebo historie migrací.

Při návratu zastavte aplikaci, obnovte původní kód a databázi ze zálohy, vraťte
konfiguraci Supervisoru k původnímu prostředí, obnovte statické soubory původní
verzí `collectstatic` a teprve potom aplikaci spusťte. Po návratu databáze
se ztratí změny obsahu provedené po záloze; proto úpravy obnovte až po ověření.

## Dokumentace

- [Kompatibilita a postup upgradu Wagtailu](https://docs.wagtail.org/en/stable/releases/upgrading.html)
- [Wagtail 7.4 LTS](https://docs.wagtail.org/en/stable/releases/7.4.html)
- [Python a virtuální prostředí na Roští](https://docs.rosti.cz/cs/apps/python/)
- [Nasazení a Supervisor na Roští](https://docs.rosti.cz/cs/quickstart/first_deployment/)
