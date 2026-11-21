# Transcriptor na webu – jednorázové nastavení krok za krokem

Po tomto nastavení otevřete Transcriptor na adrese typu `https://prepis-ales.streamlit.app`
z mobilu i z obou počítačů. Přihlašujete se svým účtem Google a nikdo jiný se dovnitř nedostane.
Přepisy se ukládají na váš Google Disk do složky **Transcriptions**.

Celé nastavení zabere asi 20–30 minut a dělá se jen jednou. Postupujte po krocích, nic nepřeskakujte.
Všechno je zdarma, platíte jen přepisy (Soniox) a překlady (Gemini) jako doteď.

Budete potřebovat:
- počítač s prohlížečem (nastavení se dělá na PC, ne v mobilu),
- přihlášení na GitHub (účet `coooach-you`),
- své dva klíče: Soniox a Gemini. Najdete je v souboru `C:\Transcriptor\.env`.
  Klikněte na něj pravým tlačítkem → **Otevřít v programu** → **Poznámkový blok**.

---

## Krok 0: Vyberte si adresu aplikace

Vymyslete krátký název, třeba `prepis-ales`. Adresa pak bude `https://prepis-ales.streamlit.app`.
Jsou povolená malá písmena, číslice a pomlčky. Název si napište, budete ho potřebovat několikrát.
V návodu ho píšu jako **NAZEV**.

---

## Krok 1: Schvalte nový kód na GitHubu

1. Otevřete odkaz na „pull request“, který jsem vám poslal v chatu.
2. Dole klikněte na zelené tlačítko **Merge pull request** a pak **Confirm merge**.

Tím se webová verze dostane do hlavní větve `main`, odkud ji Streamlit spustí.

---

## Krok 2: Google Cloud – povolení přihlášení a přístupu k Disku

Tady Googlu řeknete, že aplikace Transcriptor smí přihlašovat váš účet a ukládat na váš Disk.

### 2a. Založte projekt
1. Otevřete <https://console.cloud.google.com> a přihlaste se účtem `coooach@gmail.com`.
   Při první návštěvě odsouhlaste podmínky.
2. Nahoře vlevo klikněte na výběr projektu (vedle loga Google Cloud) → **Nový projekt**.
3. Název: `Transcriptor` → **Vytvořit**. Počkejte pár sekund a nahoře projekt **Transcriptor** vyberte.

### 2b. Zapněte Google Drive API
1. Zkontrolujte, že je nahoře vybraný projekt **Transcriptor**.
2. Otevřete odkaz <https://console.cloud.google.com/apis/library/drive.googleapis.com>.
3. Klikněte na modré tlačítko **Povolit** (Enable). Když místo něj vidíte **Spravovat** (Manage),
   je API už zapnuté.

### 2c. Nastavte přihlašovací obrazovku
1. Otevřete odkaz <https://console.cloud.google.com/auth/overview> (stránka se jmenuje
   „Google Auth Platform“, dříve „Obrazovka souhlasu OAuth“). Nahoře musí být vybraný projekt **Transcriptor**.
2. Klikněte na **Začínáme** (Get started) a vyplňte:
   - Název aplikace: `Transcriptor`
   - E-mail podpory: váš e-mail
   - Okruh uživatelů (Audience): **Externí** (External)
   - Kontaktní e-mail: váš e-mail
   - odsouhlaste podmínky → **Vytvořit**
3. Vlevo otevřete **Okruh uživatelů** (Audience) a klikněte na **Publikovat aplikaci**
   (Publish app) → **Potvrdit**. Stav se změní na „V produkci“.
   *Proč: v testovacím režimu Google povolení ke Disku po 7 dnech zruší.*
   Google aplikaci neověřuje, to je pro osobní použití v pořádku.

### 2d. Vytvořte přístupové údaje
1. Vlevo otevřete **Klienti** (Clients), nebo rovnou <https://console.cloud.google.com/auth/clients>, a klikněte na **Vytvořit klienta** (Create client).
2. Typ aplikace: **Webová aplikace** (Web application). Název: `Transcriptor`.
3. U **Autorizované identifikátory URI přesměrování** (Authorized redirect URIs)
   klikněte dvakrát na **Přidat URI** a vložte tyto dvě adresy (NAZEV nahraďte svým):
   ```
   https://NAZEV.streamlit.app/oauth2callback
   https://NAZEV.streamlit.app/
   ```
   Pozor na lomítko na konci té druhé.
4. Klikněte na **Vytvořit**. Zobrazí se **ID klienta** (Client ID) a **Tajný klíč klienta**
   (Client secret). Oba si zkopírujte do Poznámkového bloku. Tajný klíč nikomu neposílejte.

---

## Krok 3: Připravte nastavení (Secrets)

V Poznámkovém bloku si připravte tento text a doplňte svoje hodnoty:

```toml
SONIOX_API_KEY = "sem váš Soniox klíč"
GEMINI_API_KEY = "sem váš Gemini klíč"
ALLOWED_EMAILS = "coooach@gmail.com"
DRIVE_FOLDER = "Transcriptions"
DRIVE_REFRESH_TOKEN = ""

[auth]
redirect_uri = "https://NAZEV.streamlit.app/oauth2callback"
cookie_secret = "sem napište aspoň 40 náhodných písmen a číslic"
client_id = "sem ID klienta z kroku 2d"
client_secret = "sem tajný klíč klienta z kroku 2d"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

- Klíče zkopírujte ze souboru `.env` (bez `SONIOX_API_KEY=`, jen samotný klíč).
- `cookie_secret` si vymyslete: naťukejte náhodně aspoň 40 písmen a číslic. Nikde jinde ho nepotřebujete.
- Řádek `DRIVE_REFRESH_TOKEN = ""` zatím nechte prázdný, doplníte ho v kroku 5.
- Uvozovky kolem hodnot musí zůstat.

---

## Krok 4: Spusťte aplikaci na Streamlit Community Cloud

1. Otevřete <https://share.streamlit.io> → **Continue with GitHub** a povolte přístup
   (Authorize). Pokud se ptá na přístup k soukromým repozitářům, povolte ho.
2. Vpravo nahoře klikněte na **Create app** → **Deploy a public app from GitHub**
   (nebo „Yup, I have an app“).
3. Vyplňte:
   - Repository: `coooach-you/TRANSCRIPTOR`
   - Branch: `main`
   - Main file path: `app.py`
   - App URL: **NAZEV** (ten z kroku 0)
4. Klikněte na **Advanced settings**:
   - Python version: **3.13**
   - Do pole **Secrets** vložte celý text z kroku 3.
   - **Save**
5. Klikněte na **Deploy**. První spuštění trvá pár minut (instalují se knihovny).

Aplikace je chráněná přihlášením přes Google, takže nevadí, že GitHub ji nazývá „public app“.

---

## Krok 5: Přihlaste se a připojte Google Disk (jen poprvé)

1. Otevřete `https://NAZEV.streamlit.app` a klikněte na **Přihlásit přes Google**.
2. Google může ukázat varování **„Google tuto aplikaci neověřil“**. Je to vaše vlastní aplikace,
   takže klikněte na **Rozšířená nastavení** (Advanced) → **Přejít do aplikace Transcriptor**.
3. Aplikace ukáže stránku **Připojení Google Disku** → klikněte na **Povolit přístup ke Google Disku**.
4. Vyberte svůj účet, znovu případně potvrďte varování a **zaškrtněte** povolení k Disku → **Pokračovat**.
5. Aplikace ukáže řádek začínající `DRIVE_REFRESH_TOKEN = "1//…`. Zkopírujte ho ikonou vpravo v rámečku.
6. Na <https://share.streamlit.io> u své aplikace klikněte na **⋮** → **Settings** → **Secrets**.
   Řádek `DRIVE_REFRESH_TOKEN = ""` nahraďte zkopírovaným řádkem → **Save**.
7. Počkejte asi minutu a stránku aplikace obnovte. Hotovo, uvidíte běžný Transcriptor.

---

## Krok 6: Ikona na ploše mobilu

1. V mobilu otevřete v Chromu `https://NAZEV.streamlit.app` a přihlaste se.
2. Vpravo nahoře **⋮** → **Přidat na plochu** (nebo „Instalovat aplikaci“) → **Přidat**.

### Jak přepsat nahrávku z mobilu
1. Nahrajte rozhovor v Diktafonu, nahráváním obrazovky nebo jiné aplikaci, jak jste zvyklý.
2. Otevřete Transcriptor z ikony na ploše.
3. Klepněte na **Browse files** (Procházet soubory) a vyberte nahrávku.
4. Klepněte na **Spustit přepis**.

Dřívější přepisy najdete pod šipkou **»** vlevo nahoře (postranní panel).

**Když zavřete prohlížeč během přepisu:** nic se neztratí. Při dalším otevření se nahoře
ukáže **„Rozpracovaný přepis“** a tlačítko **Dokončit**.

**Uspávání:** když aplikaci pár dní nikdo neotevře, Streamlit ji uspí. Pak se ukáže tlačítko
„Yes, get this app back up“. Klepněte na něj a za chvilku aplikace naběhne.

---

## Verze na počítači (záloha)

Verze na PC funguje dál beze změny. Aby web i PC viděly stejné přepisy, nastavte v ní
složku pro ukládání na `G:\Můj disk\Transcriptions` (postranní panel → **Složka pro ukládání**).

---

## Když něco nejde

| Co vidíte | Co udělat |
|---|---|
| „Účet … nemá do aplikace přístup“ | V Secrets zkontrolujte `ALLOWED_EMAILS`, musí tam být přesně váš e-mail. |
| Google hlásí „redirect_uri_mismatch“ | V kroku 2d chybí nebo nesedí adresa. Zkontrolujte NAZEV a lomítko na konci. |
| „Povolení pro Google Disk vypršelo“ | Otevřete `https://NAZEV.streamlit.app/?pripojit=disk` a zopakujte krok 5 (body 3–7). |
| „V Secrets chybí SONIOX_API_KEY…“ | Doplňte klíče v Settings → Secrets. |
| Aplikace se nenačte vůbec | Na share.streamlit.io u aplikace **⋮** → **Reboot app**. Pomůže i **Manage app** vpravo dole, kde je vidět chyba. |
