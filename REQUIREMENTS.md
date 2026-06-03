Cieľom zadania je monitorovať resp. riadiť signály získané z reálnych senzorov resp. simulačných a virtuálnych prostredí. Monitorovanie resp. riadenie sa má uskutočňovať prostredníctvom webovej aplikácie, aby bola naplnená koncepcia IoT.

Hardvér a softvér je podľa individuálnych možností. Preferuje sa využitie reálnej platformy Arduino a Raspberry.

Štandardnou úlohou je vytvoriť webovú aplikáciu v jazyku Python na platforme Raspberry Pi, ktorá bude realizovať nasledovné funkcie:

1.       spustenie aplikácie tlačidlom Open, ktoré bude slúžiť na inicializáciu systému, nadviazanie spojenia a aktiváciu senzorov a akčných členov

2.       nastavenie parametrov monitorovania resp. regulácie

3.       odštartovanie monitorovania resp. regulácie tlačidlom Start

4.       výpis monitorovaných resp. regulovaných údajov vo forme zoznamu v prehliadači klienta

5.       zobrazovanie monitorovaných resp. regulovaných údajov vo forme grafov v prehliadači klienta

6.       zobrazovanie monitorovaných resp. regulovaných údajov vo forme ručičkových ukazovateľov (cíferníkov) v prehliadači klienta

7.        archiváciu monitorovaných resp. aj  akčných signálov a nastavených parametrov prostredníctvom ukladania do databázy (aj s možnosťou ich výpisu a vykreslenia)

8.        archiváciu monitorovaných resp. aj  akčných signálov a nastavených parametrov prostredníctvom zápisu do súboru (aj s možnosťou ich výpisu a vykreslenia)

9.       zastavenie monitorovania resp. regulácie tlačidlom Stop

10.       ukončenie aplikácie tlačidlom Close, ktoré bude slúžiť na deaktiváciu systému a ukončenie spojenia

Neštandardné úlohy by sa mali k tejto funkcionalite priblížiť pokiaľ to je možné, ale budú hodnotené individuálne. Najviac budú oceňované úlohy s reálnym hardvérom a s reguláciou resp. ovládaním. V takom prípade stačí regulovať jednu veličinu. V prípade reálnych zadaní, ktoré majú iba monitorovanie/sledovanie treba vizualizovať aspoň 2 signály (aspoň 2 senzory) a umožniť prepínanie medzi nimi.

Ku každému bodu je potrebné vytvoriť serverovú aj klientskú časť, pričom úlohou serverovej časti je zvyčajne monitorovanie resp. riadenie a hardvérová realizácia a úlohou klientskej časti je ovládanie a vizualizácia (numericky, graficky - grafy, cíferníky, posuvníky...).

K vytvorenému dielu je potrebné napísať technickú dokumentáciu v rozsahu min. 5 strán formátu A4. Technická dokumentácia bude obsahovať vývojársku a používateľskú príručku. Technickú dokumentáciu (vo formáte DOC alebo PDF) spolu s vytvorenou aplikáciou (vrátane zdrojových súborov) odovzdávate elektronicky prostredníctvom systému Moodle ako jeden zozipovaný súbor. Ak by bol súbor väčší ako 10 MB, umiestnite ho na dostupné úložisko a do Moodle nahrajte iba link na stiahnutie.

Pri vývoji aplikácie je potrebné používať verzionovací systém GitHub (prípadne Bitbucket, GitLab, ...), pričom jednotlivé príspevky musia byť vhodne komentované a v technickej dokumentácii musí byť uvedená adresa úložiska (prípadne ďalšie prístupové údaje).

Skúšajúca komisia ohodnotí vypracované zadanie na základe vytvoreného diela, napísanej dokumentácie a obhajoby zadania v deň skúšky absolútnym počtom bodov (max. 28 bodov). Na obhajobu si netreba pripravovať prezentáciu, stačí použiť dokumentáciu.

Približný percentuálny rozpis bodovania je nasledovný:
- zdokumentovaný návrh architektúry celej aplikácie (vrátane UML diagramov a komunikačných protokolov) 15%
- návrh a realizácia serverovej časti 15%,
- návrh a realizácia klientskej časti 10%,
- každý z bodov 1. - 10. cca 5%,
- technická dokumentácia (vrátane verzionovacieho systému 10%).

Upozornenie: Vypracované zadanie je potrebné odovzdať do určeného termínu (viď. údaj "Termín odovzdania" nižšie). Penalizácia za každý deň omeškania je 10% z max. počtu bodov.