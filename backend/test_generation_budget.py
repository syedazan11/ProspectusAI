from __future__ import annotations

from src.generation.answer_service import RescueAnswerService


CASES = [
    (
        "eligibility for mechanical",
        """
4.2.2 Admission Eligibility
An applicant must have passed Higher School Examination (HSC) I & II
or an equivalent qualification in the relevant discipline.
The applicant must also pass the Pre-admission Entry Test with at least
50% marks.
""",
        False,
    ),
    (
        "fee for mechanical",
        """
8.1.1 For Main Campus, LEJ and City Campus
For locals: All BE, BS & B.Arch except specified programmes — Rs. 57,000/-
For Foreigners — Rs. 359,000/-
8.1.2 For TIEST
A separate fee structure applies to TIEST.
""",
        False,
    ),
    (
        "seat distribution",
        """
Regular Scheme
Programme A: 60 seats
Programme B: 40 seats

Self-Finance Scheme
Programme A: 20 seats
Programme B: 15 seats
""",
        True,
    ),
    (
        "hostel facilities",
        """
University-wide Facilities
Library, medical centre, sports complex.

Hostel Facilities
Muhammad Bin Qasim Hostel I
- 35 dormitory rooms
- 20 cubicle rooms

Girls Hostel
- common rooms
""",
        False,
    ),
]


def main() -> None:
    service = object.__new__(RescueAnswerService)

    system = service._system_prompt()

    print("========== GENERATION BUDGET TEST ==========")
    print(f"system_chars={len(system)}")
    print(f"system_est_tokens={len(system) // 4}")
    print("")

    required_rules = (
        "Use ONLY the supplied prospectus context",
        "Never mix departments",
        "Preserve row/column relationships",
        "For programme eligibility",
        "For admission fees",
        "Use only meanings explicitly supported",
    )

    missing = [
        rule for rule in required_rules
        if rule.casefold() not in system.casefold()
    ]

    if missing:
        raise AssertionError(
            "Missing critical system rules:\n- "
            + "\n- ".join(missing)
        )

    for number, (question, context, complex_table) in enumerate(CASES, 1):
        prompt = service._build_prompt(
            question=question,
            context=context,
            has_complex_table=complex_table,
        )

        combined = len(system) + len(prompt)

        print(
            f"[CASE {number}] {question}\n"
            f"  context_chars={len(context)}\n"
            f"  prompt_chars={len(prompt)}\n"
            f"  prompt_est_tokens={len(prompt) // 4}\n"
            f"  combined_est_tokens={combined // 4}\n"
        )

    print("PASS: generation prompt construction is offline-testable.")
    print("No Groq request was made.")


if __name__ == "__main__":
    main()