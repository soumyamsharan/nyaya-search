## ADDED Requirements

### Requirement: Searchable filter fields
Each filter field that has a fixed or listed set of values (judges on the bench, judgment author, outcome, match in, Act,
section) SHALL show the options that match the text typed so far, and SHALL show a control that opens and closes the list.
Option names SHALL be shown in full, with wrapping where needed.

#### Scenario: Typing narrows the list
- **WHEN** a user types "Pard" in Judges on bench
- **THEN** only judges whose names match are listed, with their judgment counts

#### Scenario: Two judges with the same first name
- **WHEN** two judges share a first name
- **THEN** each is listed with its full name, so the user can tell them apart

#### Scenario: Opening the list without typing
- **WHEN** a user clicks the arrow at the right of a field
- **THEN** the full list opens, and clicking the arrow again closes it

#### Scenario: Keyboard use
- **WHEN** the list is open and the user presses the arrow keys then Enter
- **THEN** the highlighted option is chosen; Escape closes the list

### Requirement: Act and section pickers
The Act field SHALL match Acts by their name and by the words of their short key, so "negotiable" finds the Negotiable
Instruments Act (shown as NI Act). The Section field SHALL list the sections of the Act chosen in the Act field, and SHALL
ask the user to choose an Act first when none is chosen. Typed text that matches no listed option SHALL still be accepted.

#### Scenario: Section choices follow the Act
- **WHEN** a user chooses the NI Act and types "13" in Section
- **THEN** Section 138 and Section 139 are listed with their judgment counts

#### Scenario: No Act chosen
- **WHEN** no Act is chosen
- **THEN** the Section field says to choose an Act first

### Requirement: Date fields
Decided from and Decided to SHALL accept a typed date in dd/mm/yyyy or yyyy-mm-dd, and SHALL offer a calendar opened by a
button. The calendar SHALL let the user choose the month and year directly, with years from 1950 to the current year. The
calendar SHALL close after a date is chosen, after Clear, or on any click outside it. Dates SHALL be sent as yyyy-mm-dd.

#### Scenario: Going to a distant date
- **WHEN** a user wants October 2009
- **THEN** they choose the year and the month from the dropdowns and pick the day, without stepping month by month

#### Scenario: Invalid typed date
- **WHEN** a user types a date that does not exist, such as 31/02/2025
- **THEN** the field returns to its previous value and no date is applied

### Requirement: Filters in a collapsible panel
The filter fields SHALL sit in a panel labelled "Refine search" that is collapsed by default, is open when any filter is set,
and shows how many filters are set.

#### Scenario: Filter set from a link
- **WHEN** a search link includes a filter
- **THEN** the panel opens and shows the number of filters set
