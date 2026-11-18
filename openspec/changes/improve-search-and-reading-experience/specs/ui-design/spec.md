## ADDED Requirements

### Requirement: Editorial visual design
The site SHALL use a warm paper background, dark ink text and a single deep green accent. Headings and judgment text SHALL
use a serif typeface; interface text SHALL use a sans-serif typeface. Colours SHALL be defined once as theme tokens.

#### Scenario: Judgment text
- **WHEN** a user reads a judgment paragraph
- **THEN** the text is set in the serif typeface with generous line spacing

### Requirement: Search results layout
Search results SHALL appear as a numbered, ruled list. Each result title SHALL be underlined in the accent colour so that it
reads as a link before the user hovers over it.

#### Scenario: Result title
- **WHEN** a search returns results
- **THEN** each title is underlined and opens the judgment

### Requirement: Pointer on clickable elements
Buttons, summaries, selects and clickable options SHALL show a hand pointer on hover. Disabled buttons SHALL show a
not-allowed pointer.

#### Scenario: Hovering a button
- **WHEN** a user hovers over an enabled button
- **THEN** the pointer changes to a hand

#### Scenario: Disabled button
- **WHEN** a button is disabled
- **THEN** the pointer shows that it cannot be pressed

### Requirement: Phone width
Every page SHALL fit a phone-width screen (375 pixels) with no horizontal scrolling and with a 16 pixel side margin.

#### Scenario: Search on a phone
- **WHEN** a user opens search on a 375-pixel screen
- **THEN** the page fits the screen without sideways scrolling
