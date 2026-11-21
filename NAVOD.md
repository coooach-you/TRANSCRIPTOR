# Transcriptor – návod krok za krokem (Windows 11 a 10)

Tento návod vás provede vším od nuly. Celé to zabere asi 20 minut a dělá se to jen jednou.
Potom už aplikaci spouštíte dvojklikem.

**Co budete potřebovat:** počítač s Windows 11 nebo Windows 10 (64bitová verze), připojení k internetu, klíč Soniox a klíč Gemini
(ty už máte).

**Webová verze pro mobil a další počítače:** viz samostatný návod `NAVOD_WEB.md`.

---

## Krok 1: Nainstalujte Python

Python je program, ve kterém aplikace běží.

1. Otevřete stránku **https://www.python.org/downloads/windows/**.
2. Najděte nejnovější **Python 3.14.x** (teď 3.14.10) a klikněte na odkaz
   **„Download Windows installer (64-bit)“**. Stáhne se soubor `python-3.14.10-amd64.exe`.
   - Nahoře stránka nabízí i „Python install manager“. Ten taky funguje, ale tento návod
     popisuje klasický instalátor, protože je pro začátek jednodušší.
   - Python 3.13 nebo 3.14, který už máte nainstalovaný, je v pořádku a nemusíte nic měnit.
3. Spusťte stažený soubor.
4. ⚠️ **Důležité:** úplně dole v prvním okně zaškrtněte **„Add python.exe to PATH“**.
   Bez toho by aplikace Python nenašla.
5. Klikněte na **Install Now** a počkejte, až se objeví „Setup was successful“. Zavřete okno.

**Ověření:** Stiskněte klávesu Windows, napište `cmd` a stiskněte Enter. Do černého okna napište
`python --version` a stiskněte Enter. Má se objevit např. `Python 3.14.10`.
Pokud se místo toho otevře Microsoft Store nebo se objeví chyba, Python se nenainstaloval
s volbou PATH. Spusťte instalátor znovu, zvolte **Modify → Next** a zaškrtněte
**„Add Python to environment variables“**.

---

## Krok 2: Stáhněte aplikaci

1. Stáhněte soubor **transcriptor.zip** (je přiložený u zprávy v Claude).
2. Otevřete složku **Stažené soubory**, klikněte na `transcriptor.zip` pravým tlačítkem
   a zvolte **Extrahovat vše…**.
3. Jako cíl napište `C:\Transcriptor` a klikněte na **Extrahovat**.

Ve složce `C:\Transcriptor` teď máte mimo jiné soubory `app.py`, `instalovat.bat`,
`spustit.bat` a tento návod.

---

## Krok 3: Nainstalujte knihovny (jen jednou)

1. Ve složce `C:\Transcriptor` dvakrát klikněte na **`instalovat.bat`**.
2. Pokud Windows zobrazí modré okno „Systém Windows ochránil váš počítač“, klikněte na
   **Další informace → Přesto spustit**. (Soubor jen instaluje knihovny, obsah si můžete
   prohlédnout v Poznámkovém bloku.)
3. Otevře se černé okno a začnou běžet řádky textu. Trvá to 1 až 3 minuty.
4. Když se objeví **„Hotovo! Aplikaci spustíte dvojklikem na spustit.bat“**, stiskněte
   libovolnou klávesu. Okno se zavře.

Pokud se objeví **„CHYBA: Python není nainstalovaný“**, vraťte se ke kroku 1.

---

## Krok 4: Spusťte aplikaci

1. Dvakrát klikněte na **`spustit.bat`**.
2. Otevře se černé okno (to **nechte otevřené**, v něm aplikace běží) a za pár sekund
   se v prohlížeči sama otevře stránka **Transcriptor**.
   Pokud se neotevře, napište do prohlížeče adresu `http://localhost:8501`.
3. Pokud se Windows zeptá na povolení přístupu k síti (brána firewall), klikněte na **Povolit**.

**Ukončení:** zavřete černé okno. Zavřením jen záložky v prohlížeči aplikace dál běží na pozadí.

> Tip: Na `spustit.bat` klikněte pravým tlačítkem → **Zobrazit další možnosti → Odeslat →
> Plocha (vytvořit zástupce)**. Pak aplikaci spouštíte z plochy.

---

## Krok 5: Vložte klíče (jen poprvé)

1. V levém panelu aplikace vložte do políčka **Soniox API klíč** svůj klíč ze Sonioxu.
2. Do políčka **Gemini API klíč** vložte klíč z Google AI Studio.
3. Klikněte na **💾 Zapamatovat klíče**.

Klíče se uloží do souboru `.env` ve složce `C:\Transcriptor` a příště se načtou samy.
Tento soubor nikomu neposílejte.

Kde klíče najdete, kdybyste je potřebovali znovu:
- Soniox: https://console.soniox.com → **API Keys**
- Gemini: https://aistudio.google.com/apikey

---

## Krok 6: První přepis

1. **Nahrávka:** přetáhněte audio soubor do pole „Audio soubor“ nebo klikněte na
   **Browse files**. Podporované jsou mp3, m4a, wav, ogg a další, nahrávka může mít až 5 hodin.
2. **Jazyky v nahrávce:** ve výchozím stavu je čeština a angličtina. Nechte to tak, pokud se
   mluví jinak, přidejte jazyk.
3. **Jména a odborné pojmy** (nepovinné): napište jména účastníků, firem nebo zkratky,
   oddělené čárkou, např. `Aleš Novák, Transcriptor, KPI`. Soniox je pak zapíše správně.
4. **Rovnou přeložit:** zaškrtněte, pokud chcete překlad (např. anglickou nahrávku do češtiny).
   Překlad jde udělat i později.
5. Klikněte na **▶️ Spustit přepis**.

Soubor se nahraje do Sonioxu a ten ho přepíše. Hodinová nahrávka obvykle trvá pár minut.
Aplikace mezitím ukazuje, jak dlouho už čeká. Nezavírejte prohlížeč ani černé okno.

Po dokončení aplikace ukáže délku a cenu (hodina stojí asi 0,10 USD). Soniox pak soubor
i přepis na svém serveru smaže.

---

## Krok 7: Pojmenujte mluvčí

Soniox pozná, kdo mluví, ale nezná jména. Označí lidi jako „Mluvčí 1“, „Mluvčí 2“ atd.

1. Rozbalte **👥 Jména mluvčích**.
2. Pod každým mluvčím je ukázka toho, co říkal. Podle ní poznáte, kdo to je.
3. Do políčka napište jméno a stiskněte Enter.

Jména se hned propíšou do přepisu, překladu i do souborů ke stažení.
Pojmenujte mluvčí **ještě před generováním shrnutí**, aby v něm byla správná jména.

---

## Krok 8: Přepis, překlad a stažení

- Záložka **Přepis** ukazuje text ve tvaru `[00:12:34] Aleš: …`.
- Záložka **Překlad** se objeví, pokud jste překládali.
- Když máte překlad, nad textem zvolíte **Uspořádání přepisu a překladu**:
  - **Zvlášť**: přepis a překlad jsou dva samostatné dokumenty (`prepis` a `preklad`).
  - **Dohromady**: jeden dokument, kde je vždy úsek v původním jazyce (zhruba minuta, nebo
    do změny mluvčího) a hned pod ním jeho překlad:
    ```
    [00:12:34] Aleš: We should finish the budget by Friday.
    » Rozpočet bychom měli dokončit do pátku.
    ```
    Ve Wordu je originál normálně a překlad kurzívou. Soubor se jmenuje `prepis_a_preklad`.
  - Volba se pamatuje i pro další nahrávky a jde kdykoli přepnout. Soubory ve složce
    (i na Google Disku) se po přepnutí hned předělají.
- Pod textem jsou tlačítka **⬇️ TXT**, **⬇️ Markdown** a **⬇️ Word**.
- Překlad do jiného jazyka (nebo dodatečný překlad) spustíte v části **🌍 Přeložit přepis**.

---

## Krok 9: Shrnutí

1. V části **3. Shrnutí** vyberte **šablonu**:
   - **Stručný přehled**: o čem nahrávka byla a hlavní body
   - **Detailní zápis z porady**: účastníci, témata, rozhodnutí, úkoly, otevřené otázky
   - **Seznam úkolů**: kdo má co udělat a do kdy
   - **Analýza tónu**: atmosféra, postoje a napětí, s citacemi
2. Vyberte **jazyk shrnutí** (výchozí je čeština).
3. **Vycházet z:** z přepisu (původní jazyk), nebo z překladu.
4. Klikněte na **✨ Generovat shrnutí**.

Můžete vygenerovat víc šablon za sebou. Všechna shrnutí zůstanou pod sebou a každé jde
stáhnout jako TXT, Markdown nebo Word. Generování znovu stejnou šablonou starou verzi přepíše.

---

## Kde najdu uložené výsledky

Všechno se ukládá samo, ve výchozím stavu do složky **`C:\Transcriptor\vystupy`**.
Po nastavení Google Disku (další kapitola) se ukládá tam. Každá nahrávka má vlastní
podsložku s datem, např. `2026-11-21_2130_porada`, a v ní:
- `prepis` a `preklad` (nebo `prepis_a_preklad`), vždy jako .txt i .docx
- `shrnuti_….md` a `shrnuti_….docx` (Word verze se dobře čte na mobilu)
- `data.json`: data pro aplikaci, nemazat

Přepis se uloží hned po dokončení, ještě před překladem. Zaplacená práce se tedy neztratí,
ani když zavřete prohlížeč.

**Návrat ke starší nahrávce:** v levém panelu v části **📂 Dřívější přepisy** vyberte
nahrávku a klikněte na **Otevřít**. Můžete přejmenovat mluvčí nebo vygenerovat další shrnutí
a za nový přepis nic neplatíte.

**Další nahrávka:** klikněte v levém panelu na **➕ Nová nahrávka**.

---

## Přepisy na dvou počítačích a v mobilu (Google Disk)

Přepisy se budou ukládat do Google Disku. Oba počítače pak vidí stejné přepisy a v mobilu
si je přečtete v aplikaci Google Disk. Postup udělejte **na každém počítači zvlášť**.

### A. Nainstalujte Google Disk pro počítač
1. Otevřete **https://www.google.com/drive/download/** a klikněte na
   **Stáhnout Disk pro počítač**.
2. Spusťte stažený soubor `GoogleDriveSetup.exe` a nechte ho doběhnout.
3. Přihlaste se svým účtem Google. Na obou počítačích použijte **stejný účet**.
4. V Průzkumníku souborů se objeví nová jednotka, obvykle **`G:`**, a v ní složka
   **Můj disk** (v anglických Windows **My Drive**).

### B. Vytvořte složku pro přepisy
1. Otevřete Průzkumník souborů (klávesa Windows + E) a jděte na **G: → Můj disk**.
2. Klikněte pravým tlačítkem → **Nový → Složka** a pojmenujte ji `Transcriptor`.
   (Na druhém počítači ji už nevytvářejte, objeví se tam sama.)
3. Klikněte na složku, nahoře do řádku s adresou klikněte a cestu zkopírujte (Ctrl + C).
   Bude vypadat např. takto: `G:\Můj disk\Transcriptor`.

### C. Nastavte složku v aplikaci
1. Spusťte Transcriptor.
2. V levém panelu v části **📂 Dřívější přepisy** rozbalte **Složka pro ukládání**.
3. Do políčka **Cesta ke složce** vložte zkopírovanou cestu (Ctrl + V) a klikněte na
   **Uložit složku**. Aplikace si ji zapamatuje stejně jako klíče.

Na druhém počítači zopakujte kroky A a C (a samozřejmě instalaci aplikace, kroky 1 až 5).
Pokud tam Google Disk dostal jiné písmeno jednotky, použijte cestu, kterou vidíte na tomto počítači.

**Starší přepisy ze složky `C:\Transcriptor\vystupy`** můžete do Google Disku jednoduše
přesunout: přetáhněte podsložky do `G:\Můj disk\Transcriptor`.

### D. Mobil (Android)
1. Otevřete aplikaci **Disk Google** (bývá v telefonu předinstalovaná, jinak ji najdete
   v Obchodě Play). Přihlaste se stejným účtem.
2. Otevřete složku **Transcriptor** a v ní nahrávku. Nejlépe se čtou soubory
   `shrnuti_….docx` a `prepis.txt`.
3. Přepisovat se dá jen na počítači. Mobil slouží ke čtení.

### Když pracujete na obou počítačích najednou
- Nový přepis z jednoho počítače se na druhém objeví v seznamu **Dřívější přepisy** během
  minuty (podle rychlosti synchronizace Google Disku).
- Když máte stejný přepis otevřený na obou počítačích, aplikace při každém uložení přepíše
  jen to, co jste právě změnili. Shrnutí vytvořené na druhém počítači se tedy nesmaže.
  Jakmile druhý počítač něco uloží, aplikace načte novější verzi a ukáže hlášku
  „Načtena novější verze z druhého zařízení“.
- Jediný případ, kdy něco přepíšete: když na obou počítačích současně přejmenujete stejného
  mluvčího. Platí potom to jméno, které se uložilo později.
- Pokud se ve složce objeví soubor jako `data (1).json`, jde o konflikt Google Disku.
  Aplikace ho ignoruje a můžete ho smazat.

---

## Kolik to stojí

| Služba | Za co | Přibližná cena |
|---|---|---|
| Soniox | přepis včetně mluvčích | 0,10 USD za hodinu audia |
| Gemini | překlad a shrnutí | jednotky centů za hodinovou nahrávku |

Útratu sledujete na https://console.soniox.com (Billing) a https://aistudio.google.com
(Usage). V obou se dá nastavit limit.

---

## Když něco nejde

| Problém | Řešení |
|---|---|
| Po dvojkliku na `.bat` okno hned zmizí | Spusťte `instalovat.bat` znovu a přečtěte si chybu. Nejčastěji chybí Python v PATH (krok 1). |
| „Nejdřív spusťte instalovat.bat“ | Krok 3 neproběhl. Spusťte `instalovat.bat`. |
| Prohlížeč se neotevře | Napište adresu `http://localhost:8501`. |
| „Chybí Soniox API klíč“ | Vložte klíč v levém panelu a klikněte na Zapamatovat klíče. |
| Chyba 401 / „unauthorized“ / „invalid api key“ | Klíč je špatně zkopírovaný. Vytvořte nový a uložte ho znovu. Nejdřív smažte soubor `.env` ve složce `C:\Transcriptor`. |
| Chyba 402 / „insufficient balance“ / „quota“ | Na účtu Soniox nebo Google došel kredit, nebo není nastavená platba. |
| Gemini hlásí „model not found“ | Google model vypnul. V levém panelu vyberte jiný model Gemini. |
| V seznamu Dřívější přepisy chybí přepis z druhého PC | Počkejte minutu, až Google Disk dosynchronizuje, a stiskněte F5. Zkontrolujte, že je na obou PC nastavená stejná složka. |
| Aplikace hlásí, že složku nejde použít | Zkontrolujte, že Google Disk běží (ikona vpravo dole u hodin) a že cesta existuje. |
| Soubor nejde nahrát | Nahrávka musí mít nejvýš 5 hodin a do 2 GB. |
| Shrnutí jsou anglicky | Zkontrolujte volbu „Jazyk shrnutí“. |

Pokud nic z toho nepomůže, zkopírujte červenou chybovou hlášku a pošlete mi ji.

---

## Aktualizace aplikace

Když od Claude dostanete nový `app.py`, prostě jím přepište ten starý ve složce
`C:\Transcriptor`. Klíče ani uložené výsledky se tím nesmažou. Pokud se změní i
`requirements.txt`, spusťte znovu `instalovat.bat`.
