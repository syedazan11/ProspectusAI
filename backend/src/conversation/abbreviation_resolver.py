from __future__ import annotations

import re


class AbbreviationResolver:

    ABBREVIATIONS = {

    # =====================================================
    # Official NED Programme Abbreviations
    # =====================================================

        "ce": "civil engineering",

        "ce(ue)": (
            "civil engineering "
            "specialisation in urban"
        ),

        "urban engineering": (
            "civil engineering "
            "specialisation in urban"
        ),

        "urban engineering": (
            "civil engineering "
            "specialisation in urban"
        ),

        "pe": "petroleum engineering",

        "ce(cn)": (
            "civil engineering "
            "specialisation in construction"
        ),

        "mech": "mechanical engineering",

        "me(au)": (
            "mechanical engineering "
            "specialisation in automotive"
        ),

        "te": "textile engineering",

        "im": (
            "industrial and manufacturing "
            "engineering"
        ),

        "ee": "electrical engineering",

        "tc": "telecommunications engineering",

        # "cs": "computer systems engineering",

        "el": "electronic engineering",

        "ch": "chemical engineering",

        # "my": "metallurgical engineering",

        "mm": "materials engineering",

        "pp": (
            "polymer and petrochemical "
            "engineering"
        ),

        "fd": "food engineering",

        "bm": "biomedical engineering",

        "se": "software engineering",

        "ct": "computer science",

        "ct*": "computer science",

        "arch": "architecture",

        "b.arch": "architecture",

        "b arch": "architecture",


        "au": (
            "mechanical engineering "
            "specialisation in automotive"
        ),

        "automotive": (
            "mechanical engineering "
            "specialisation in automotive"
        ),

        "csit": "computer science",

        "bcit": "computer science and information technology",

        "automotive engineering": (
            "mechanical engineering "
            "specialisation in automotive"
        ),

        "electrical": "electrical engineering",
        "electronic": "electronic engineering",
        "mechanical": "mechanical engineering",
        "civil": "civil engineering",
        "chemical": "chemical engineering",
        "polymer": "polymer and petrochemical engineering",
        "petrochemical": "polymer and petrochemical engineering",
        "petroleum": "petroleum engineering",

    # =====================================================
    # Common User Variations
    # =====================================================

        "eng": "engineering",

        "comp sci": "computer science",

        "computer sci": "computer science",
         "cs" : "computer science",

        "cis dept": "computer systems engineering",

        "se dept": "software engineering",

        "ee dept": "electrical engineering",

        "me dept": "mechanical engineering",

        "comp sci": "computer science",

        "comp. sci": "computer science",

        "compsci": "computer science",

        "cis": "Computer & Information Systems Engineering",

        "cse": "Computer & Information Systems Engineering",

        "cse dept": "computer systems engineering",

        "soft eng": "software engineering",

        "soft. eng": "software engineering",

        "elec eng": "electrical engineering",

        "electronic eng": "electronic engineering",

        "mech eng": "mechanical engineering",

        "mech": "mechanical engineering",

        "biomed": "biomedical engineering",

        "telecom": "telecommunications engineering",
        "telecom eng": "telecommunications engineering",
        "telecommunication": "telecommunications engineering",

        "arch": "architecture",

        "vc": "Vice-Chancellor",
        "pro vc": "Pro Vice-Chancellor",
        "pro vice": "Pro Vice-Chancellor",
        "co chair": "Co-Chairperson",
        "co chairperson": "Co-Chairperson",
        "chairman": "Chairperson",
        "chairperson": "Chairperson",
        "ncai": "National Center for Artificial Intelligence",
        "ncra": "National Center for Robotics and Automation",
        "nccs": "National Center for Cyber Security",
        "ncbc": "National Center for Big Data and Cloud Computing",
        "gym": "gymnasium",

        "gpa": "grade points",

    }

    @classmethod
    def resolve(
        cls,
        query: str,
    ) -> str:

        resolved = query

        # for abbreviation, expansion in (
        #     cls.ABBREVIATIONS.items()
        # ):
        for abbreviation, expansion in sorted(
            cls.ABBREVIATIONS.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        ):

            resolved = re.sub(

                rf"\b{re.escape(abbreviation)}\b",

                expansion,

                resolved,

                flags=re.IGNORECASE,

            )

        return resolved