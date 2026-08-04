# Bhagavad Gita

Sito multilingue generato con Quarto e pubblicato da GitHub Pages. I sorgenti
delle pagine e `_quarto.yml` vengono rigenerati da `tools/0_generate_site.py`;
per la build completa usare `run.bat`.

## Indicizzazione Google

- In Google Search Console aggiungere come proprietà con prefisso URL
  `https://enricotoffalini.github.io/BhagavadGita/`.
- Per la verifica HTML, copiare **solo il codice reale** fornito da Google nella
  variabile `GOOGLE_SITE_VERIFICATION` in `tools/0_generate_site.py`, quindi
  eseguire `run.bat`. Finché la variabile è vuota, il tag
  `google-site-verification` non viene generato.
- La sitemap è pubblicata all'indirizzo
  `https://enricotoffalini.github.io/BhagavadGita/sitemap.xml` e va inviata in
  Search Console.
- Dopo la pubblicazione, usare **Controllo URL** e **Richiedi indicizzazione**
  per la homepage e per alcune pagine principali dei capitoli.
- Queste modifiche facilitano scoperta e scansione, ma non garantiscono che
  Google indicizzi le pagine.

### Nota su `robots.txt`

Questo è un *project site* pubblicato sotto `/BhagavadGita/`. Un file collocato
in questo repository verrebbe servito come
`https://enricotoffalini.github.io/BhagavadGita/robots.txt` e **non** sarebbe
letto come `robots.txt` valido per l'host. Il solo file efficace è
`https://enricotoffalini.github.io/robots.txt`, che deve essere gestito nel
repository del sito utente `enricotoffalini.github.io`, non in questo progetto.

Se si può modificare quel repository, il file alla radice dell'host non deve
bloccare `/BhagavadGita/` e può dichiarare la sitemap, per esempio:

```text
User-agent: *
Allow: /BhagavadGita/

Sitemap: https://enricotoffalini.github.io/BhagavadGita/sitemap.xml
```
