## Why

The precedent filter was inaccurate: for judgment 2025_5_458_474 it tagged 2 paragraphs where 8 discuss earlier cases. Three causes: the rule needed a case name plus a holding verb; citation recognition ignored High Court, Delhi Law Times and English reports; and a quoted High Court judgment's own numbering split a paragraph, merging ¶14–15 into ¶29.

## What Changes

- **Cites cases filter:** a separate toggle, shown next to the role chips, that shows only paragraphs referring to an earlier case (a citation, a case name, "(supra)" or "[See: …]"). It is independent of the role rules and combines with them.
- **Inline citation annotation:** each citation inside a paragraph is highlighted. If that judgment is in the corpus, the highlight links to it (with its title on hover); otherwise it is marked "not in corpus".
- **Broader citation formats:** AIR High Court reports, Delhi Law Times and common English reports (Ch D, AC, WLR, All ER, QB, KB).
- **Parser fix:** a judgment quoting another court's own numbered paragraphs no longer swallows the judgment's following paragraphs. The numbering must resume where it left off before the quoted run is treated as quotation.

Not included: highlighting overruling language inside a cited case's name (the existing overruling flag still applies to the citing paragraph in the Citations panel).

## Capabilities

### New Capabilities

- `citation-annotations`: the cites-cases filter, inline highlights, and the broader citation formats.

## Impact

- Database: migration 005 adds `paragraphs.cites_cases`, set by the citations stage.
- Extractor version 5: all judgments are re-parsed; paragraphs whose text changed lose their embedding and are re-embedded.
- API: paragraphs carry `cites_cases` and `references` (raw citation, cited judgment id, title, citation).
- Web: the toggle, inline highlights.
