-- The reporter's cause title from the PDF header ("Ashok Singh v. State of Uttar Pradesh & Anr."), preferred over
-- the dataset's all-caps metadata title wherever a judgment is named or cited.
ALTER TABLE judgments ADD COLUMN case_name text;
