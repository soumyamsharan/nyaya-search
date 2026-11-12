from nyaya.domain import Role
from nyaya.roles import assign_roles

JUDGMENT = [
    "On 30.08.1985, Neelam breathed her last in Simaltalla. An FIR was lodged the next day.",
    "The trial court convicted the accused; the High Court affirmed the conviction.",
    "The question that arises for our consideration is whether the chain of circumstances is complete.",
    "Learned counsel for the appellant submitted that the recovery was planted.",
    "It was further submitted that the witnesses were interested.",
    "Per contra, learned counsel for the respondent-State contended that the chain is complete.",
    "Section 106 of the Evidence Act reads as under: “106. Burden of proving fact especially within knowledge.”",
    "In Sharad Birdhichand Sarda v. State of Maharashtra, this Court held that the circumstances must be fully "
    "established.",
    "We have carefully considered the submissions. In our view the prosecution has not proved its case.",
    "The motive alleged is weak and the recovery is doubtful.",
    "The appeal is accordingly allowed and the impugned judgment is set aside. No order as to costs.",
]


def test_each_spec_cue_gets_its_role():
    assert assign_roles(JUDGMENT) == [
        Role.FACTS,
        Role.FACTS,
        Role.ISSUE,
        Role.PETITIONER_ARGUMENT,
        Role.PETITIONER_ARGUMENT,  # "It was further submitted" continues the same side
        Role.RESPONDENT_ARGUMENT,
        Role.STATUTE,
        Role.PRECEDENT,
        Role.REASONING,
        Role.REASONING,
        Role.CONCLUSION,
    ]


def test_disposal_language_early_in_the_judgment_is_not_a_conclusion():
    early = ["The High Court held that the appeal is allowed.", *["Facts continue here."] * 9]
    assert assign_roles(early)[0] != Role.CONCLUSION


def test_issue_inside_a_precedent_discussion_is_precedent():
    text = "In State of Kerala v. N.M. Thomas, the issues involved were whether reservation is valid; it was held so."
    roles = assign_roles(["Facts.", "Learned counsel for the appellant submitted X.", text, "We agree.", "Disposed."])
    assert roles[2] == Role.PRECEDENT


def test_unsided_counsel_submission_takes_the_last_side():
    roles = assign_roles(["Facts.", "Per contra, learned counsel for the respondent argued Y.",
                          "Counsel submitted that the delay was explained.", "We disagree.", "End."])
    assert roles[2] == Role.RESPONDENT_ARGUMENT


def test_labelling_is_deterministic():
    assert assign_roles(JUDGMENT) == assign_roles(list(JUDGMENT))
    assert assign_roles([]) == []
