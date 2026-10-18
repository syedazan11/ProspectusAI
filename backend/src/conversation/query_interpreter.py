from __future__ import annotations
import json
import re
import time

from aiohttp import request
from src.conversation.models import (
    ConversationRequest,
    ConversationState,
    RequestType,
)
from src.conversation.abbreviation_resolver import AbbreviationResolver
from src.llm.llm_service import (
    LLMService,
)

from src.conversation.session import (
    ConversationSession,
    ConversationTopic,
)
from src.conversation.interpreter_examples import (
    FEW_SHOT_EXAMPLES,
)

class QueryInterpreter:

    INTERPRETER_RESPONSE_FORMAT = {
        "type": "json_schema",
        "json_schema": {
            "name": "prospectus_query_interpretation",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "request_type": {
                        "type": "string",
                        "enum": [
                            "greeting",
                            "goodbye",
                            "system",
                            "irrelevant",
                            "gibberish",
                            "conversation",
                            "prospectus",
                        ],
                    },
                    "rewritten_query": {
                        "type": "string",
                    },
                    "confidence": {
                        "type": "number",
                    },
                    "is_follow_up": {
                        "type": "boolean",
                    },
                    "needs_clarification": {
                        "type": "boolean",
                    },
                    "clarification_question": {
                        "type": ["string", "null"],
                    },
                    "context": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "topic": {
                                "type": [
                                    "string",
                                    "null",
                                ],
                                "enum": [
                                    "general",
                                    "people",
                                    "fees",
                                    "admission",
                                    "curriculum",
                                    "hostel",
                                    "scholarship",
                                    None,
                                ],
                            },
                            "department": {
                                "type": ["string", "null"],
                            },
                            "programme": {
                                "type": ["string", "null"],
                            },
                            "role": {
                                "type": ["string", "null"],
                            },
                            "admission_code": {
                                "type": ["string", "null"],
                            },
                            "curriculum_programme": {
                                "type": ["string", "null"],
                            },
                            "curriculum_year": {
                                "type": ["string", "null"],
                            },
                            "curriculum_semester": {
                                "type": ["string", "null"],
                            },
                            "fee_type": {
                                "type": ["string", "null"],
                            },
                        },
                        "required": [
                            "topic",
                            "department",
                            "programme",
                            "role",
                            "admission_code",
                            "curriculum_programme",
                            "curriculum_year",
                            "curriculum_semester",
                            "fee_type",
                        ],
                    },
                },
                "required": [
                    "request_type",
                    "rewritten_query",
                    "confidence",
                    "is_follow_up",
                    "needs_clarification",
                    "clarification_question",
                    "context",
                ],
            },
        },
    }

    TEMPERATURE = 0.0

    DEBUG = True

    # Official admission categories look like "R-1(A)", "SF-5", "R-3".
    # This is a structural pattern (not a hardcoded phrase list), used
    # as a safety net so an explicit code is never missed even 

    # Prospectus-context fields that are scoped to whichever
    # department/programme is currently in focus. When the user
    # switches to a different department or programme, these are
    # reset so stale info (e.g. a previous chairperson's name, an
    # old admission code) doesn't leak into the new topic.
    SCOPED_CONTEXT_FIELDS = (
        "department",
        "person_name",
        "person_role",
        "programme",
        "person_role",
        "admission_code",
        "curriculum_programme",
        "curriculum_year",
        "curriculum_semester",
        "fee_type",
    )

    CONTEXT_PRIORITY = {
        "general": 0,
        "fees": 1,
        "admission": 2,
        "people": 3,
        "curriculum": 4,
    }

    VALID_ADMISSION_CODE = re.compile(
        r"^(?:R|SF)-\d+(?:\([A-Z]\))?$",
        re.IGNORECASE,
    )

    VALID_CURRICULUM_YEAR = {
        "first year",
        "second year",
        "third year",
        "fourth year",
        "fifth year",
    }

    VALID_CURRICULUM_SEMESTER = {
        "semester 1",
        "semester 2",
    }

    INTERPRETER_SYSTEM_PROMPT = """
You are the query-understanding engine for NED University ProspectusAI.

You do NOT answer the user's question. Your job is to classify the
request, rewrite prospectus queries when necessary, detect follow-ups,
and extract prospectus context.

Return ONLY valid JSON. Never return markdown or reasoning outside JSON.

RULES

1. QUERY NORMALIZATION
- Correct obvious spelling mistakes.
- Preserve programme names already expanded by earlier processing.
- Expand an abbreviation only when its meaning is clear from the current
  message or unambiguous conversation context. (e.g. "CS" → "Computer Science", "MECH" → "Mechanical Engineering", etc).
- Never invent abbreviation expansions.
- If an abbreviation is ambiguous, preserve the user's wording.
- Keep the rewritten query grounded in the user's actual message and
  established context.

2. REWRITING
- Rewrite a prospectus query into a complete standalone question when
  needed for retrieval.
- Preserve the user's actual meaning.
- Use previous context only when the current message is genuinely
  incomplete or dependent on it.
- Do NOT add entities merely because they appeared in earlier messages
  when the current query is already complete.
- References such as "this", "that", "its", "their", "that department",
  or "that programme" are references, not new entity names.
- Never construct a new entity from a vague reference.
- If a reference cannot be resolved confidently, ask for clarification.

3. REQUEST TYPE

Classify the message as exactly one of:

- greeting
- goodbye
- system
- irrelevant
- gibberish
- conversation
- prospectus

Use these rules:

GREETING:
Normal greetings such as hi, hello, hey, salam, assalamualaikum,
good morning, good afternoon, or good evening.

GOODBYE:
Messages indicating the conversation is ending, including bye, goodbye,
see you, take care, Allah Hafiz, thanks, thank you, no thanks,
nothing thanks, that's all, that's it, or similar closing messages.

SYSTEM:
Questions about ProspectusAI itself, such as who you are, what you can do,
how you work, your capabilities, or what this system is.

CONVERSATION:
Personal statements, personal information, memory questions, or ordinary
small talk that is not about the prospectus.
Examples:
- "my name is Azan"
- "I live in Karachi"
- "what is my name?"
- "what did I tell you earlier?"
- "I like football"

IRRELEVANT:
Questions unrelated to NED University's undergraduate prospectus.
Examples:
- "what is the weather?"
- "who is the president?"
- "what is bitcoin?"
- "tell me a recipe"
anything that includes "ned", "tiest", "thar institute" is a prospectus query.

GIBBERISH:
Meaningless, random, or nonsensical input with no recognizable intent.

PROSPECTUS:
Only when the user is asking about NED University's undergraduate
prospectus, admissions, programmes, departments, fees, curriculum,
hostel, scholarships, faculty/staff, academic rules, or other information
that can reasonably be answered from the prospectus.

Do NOT classify an unrelated word as prospectus merely because prospectus
context exists.
A complete people/faculty request that specifies a role or category and
a department is not a clarification request. Interpret singular wording
as asking for the relevant person and plural or category wording as asking
for the corresponding list.
For people or faculty requests, preserve the requested role or category in context.role whenever one is specified. Do not omit it from context even when the request is plural.

4. FOLLOW-UPS
A query is a follow-up only when the current message is incomplete,
elliptical, or depends on previous conversation context.

A complete self-contained question is NOT a follow-up merely because the
previous conversation discussed the same topic.

Examples of standalone queries:
- "How much is the hostel fee?"
- "What is the duplicate degree fee?"
- "What is the admission fee for foreign students?"
- "What is the semester tuition fee?"

Short queries such as "Hostel?", "Eligibility?", "Second year?", or
"Co-chairperson?" may be follow-ups when the existing context makes their
meaning clear.

If the user explicitly names a NEW valid programme or department, replace
the previous programme/department with the new one.

If no new programme or department is established, preserve the relevant
existing context.

Example:
User: "2nd semester courses of Computer Science"
Assistant: [answer]
User: "what about 3rd semester?"
→ follow-up about 3rd semester Computer Science.

User: "and Mechanical Engineering?"
→ preserve the requested information type and semester, but switch the
programme to Mechanical Engineering:
"What are the courses in the 3rd semester of Mechanical Engineering?"

GENERIC ADMISSION DEFAULTS

Some short prospectus queries have a natural default meaning and should
NOT inherit an unrelated programme or department from previous context.

In particular:

- "eligibility"
- "eligibility criteria"
- "admission requirements"
- "requirements for admission"
- "who can apply"
- "what are the admission requirements"

should be interpreted as GENERAL ADMISSION queries unless the current
message explicitly names a programme, department, category, or other
specific scope.

For these generic admission queries:

- topic = "admission"
- department = null
- programme = null
- is_follow_up = false
- rewrite the query as a general admission question.

Do not inject a programme or department merely because the previous
conversation discussed one.

Example:

Previous context:
programme = Mechanical Engineering

Current message:
"eligibility criteria"

Correct:
"What are the eligibility criteria for admission?"

Incorrect:
"What are the eligibility criteria for admission to Mechanical Engineering?"

The previous programme may only be preserved when the current message
is genuinely incomplete and clearly depends on that programme.

5. PROGRAMME / DEPARTMENT NAMES

If the user gives ONLY a programme or department name with no requested
information, set needs_clarification=true.

Example:
"Computer Science"
→ "What would you like to know about Computer Science?"

But a programme combined with a specific request is complete:
- "fees for Computer Science"
- "chairperson of Food Engineering"
- "courses in Mechanical Engineering"
- "Computer Science second year"
- "2nd semester Mechanical Engineering"

If a recognizable shortened programme name is combined with a specific
request, resolve it to the obvious full programme name when the match is
clear. Do not ask for clarification when only the programme name is shortened.

"eligibility criteria for mechanical"
→ programme = "Mechanical Engineering"
→ needs_clarification = false

A programme plus semester/year/course information is a valid curriculum
request even if the user does not explicitly say "courses" or
"curriculum".

Do not treat broad terms such as "Engineering", "Science programme",
"institute", "university", or "campus" as a specific programme unless the
conversation clearly establishes them as one.

6. ADMISSION CODES

Valid admission codes such as:
- R-1
- R-1(A)
- R-3
- SF-1
- SF-5

are prospectus queries.

A base code such as R-1 or SF-1 represents an admission-category family.
It is not inherently ambiguous.

Requests such as:
"What is R-1?"
"Explain R-1"
"List all R-1 categories"
"What are the categories under R-1?"
refer to that admission-code family.

Do not invent its subcategories. Retrieval determines what actually exists.

7. CONTEXT

Extract only the prospectus context established or changed by the CURRENT
message.

If the current message is a clarification response to the immediately
preceding user request, preserve the relevant intent from that preceding
request while using the current message to supply the missing entity.

Context fields:

- topic: general | people | fees | admission | curriculum | hostel |
  scholarship | null
- department
- programme
- role
- admission_code
- curriculum_programme
- curriculum_year
- curriculum_semester
- fee_type

If a field is not established or changed by the current message, return null
for that field. Existing session context will preserve unchanged values.

If request_type is NOT prospectus, every context field MUST be null.

Conversation, greeting, goodbye, system, irrelevant, and gibberish messages
must never introduce prospectus context.

8. CLARIFICATION

Set needs_clarification=true only when the user's intended request cannot
reasonably be determined.

Fee-type-only queries are complete when the fee type identifies the request.
For example, "self finance fee" or "self-finance admission fee" must not
require a programme or department. Set needs_clarification=false and rewrite
the query for retrieval.

For fee queries, a fee type alone is sufficient.
NEVER ask for a programme or department when the user gives a specific fee type.
Examples: "self finance fee", "self-finance fee", "admission fee".
Set needs_clarification=false and rewrite the query for retrieval.

For an isolated programme/department name, ask what information the user
wants.

For an unresolved vague reference, ask for clarification.

When the previous assistant response asked for clarification about an
entity, and the current user message supplies that missing entity, resolve
the clarification using the immediately preceding user request.

Preserve the useful intent from the previous request.

For example:

Previous user:
"admission fee for polymer"

Assistant:
"Which programme are you referring to with 'polymer'?"

Current user:
"polymer engineering"

Correct:
- topic = "fees"
- programme = "Polymer Engineering"
- fee_type = "admission"
- needs_clarification = false
- rewrite the query as:
  "What is the admission fee for Polymer Engineering?"

Do not treat the current message as an isolated programme-name query when it
is clearly answering a clarification question.

The current message should supply or correct the missing entity while the
previous request supplies the unresolved intent.

Do not ask for clarification merely because:
- a base admission code has no subcategory;
- a programme is followed by a clear semester/year/course request;
- a complete question already contains enough information.

9. IMPORTANT BOUNDARIES

- Never answer the user's question.
- Never invent facts, entities, programmes, departments, roles, admission
  codes, or relationships.
- Never turn a personal/conversational message into a prospectus query.
- Never infer a prospectus programme from unrelated personal information.
- Curriculum has a direct route elsewhere; only classify/extract the
  request information here. Do not answer curriculum questions.

CRITICAL: Preserve the user's meaning exactly.

- Correct obvious spelling/typing mistakes when the intended word is clear.
- NEVER replace a word with a different meaning or interpretation.
- NEVER add information the user did not provide.

Example:
"electronic engineering is not electrical engineering"
"is there a moque in ned?"
→ "Is there a mosque in NED?"
NOT "What mock exams are available at NED?"
Questions about NED campus facilities, services, or student amenities
are prospectus queries when the information could be present in the
NED prospectus.

Examples:
- "Is there a mosque in NED?"
- "Does NED have a gym?"
- "Is there a stationery shop?"
- "Does NED have a sports complex?"

Do not classify these as irrelevant merely because they are not about
admissions, fees, or programmes.

JSON FORMAT

{
    "request_type": "",
    "rewritten_query": "",
    "confidence": 0.0,
    "is_follow_up": false,
    "needs_clarification": false,
    "clarification_question": null,
    "context": {
        "topic": null,
        "department": null,
        "programme": null,
        "role": null,
        "admission_code": null,
        "curriculum_programme": null,
        "curriculum_year": null,
        "curriculum_semester": null,
        "fee_type": null
    }
}

10. If gpa is mentioned, it should be interpreted as "grade points". Tell everything about gpa, grade points, and how to calculate gpa. Do not interpret gpa as "general purpose amplifier" or any other meaning.

11. when asked for facilities it also includes labs.
"""

    def __init__(
        self,
    ) -> None:

        self._llm: LLMService = LLMService()

    def interpret(
        self,
        request: ConversationRequest,
        session: ConversationSession,
    ) -> ConversationRequest:
        
        prompt_start = time.perf_counter()

        resolved_query = AbbreviationResolver.resolve(
            request.original_query,
        )


        if resolved_query != request.original_query:
            request.rewritten_query = resolved_query

        # if NameDetector.is_person_name(request.original_query):
        #     request.request_type = RequestType.PROSPECTUS
        #     request.rewritten_query = (
        #         f"Who is {request.original_query.rstrip('?.!')}?"
        #     )
        #     request.needs_clarification = False
        #     request.clarification_question = None
        #     print(
        #         f"[NAME DETECTOR] Person name detected → PROSPECTUS: "
        #         f"{request.original_query}"
        #     )

        prompt = self._build_prompt(
            request,
            session,
        )

        prompt_time = (
            time.perf_counter()
            - prompt_start
        )

        print(
            f"[INTERPRETER TIMING] Prompt build: "
            f"{prompt_time:.3f}s"
        )

        print(
            f"[INTERPRETER TIMING] System prompt chars: "
            f"{len(self.INTERPRETER_SYSTEM_PROMPT)}"
        )

        print(
            f"[INTERPRETER TIMING] User prompt chars: "
            f"{len(prompt)}"
        )

        llm_start = time.perf_counter()


        response = self._llm.generate_structured(

            system_prompt=(
                self.INTERPRETER_SYSTEM_PROMPT
            ),

            user_prompt=prompt,
            max_tokens=1000,
            reasoning_effort="low",
            response_format=self.INTERPRETER_RESPONSE_FORMAT,

        )

        print(
            "\n========== RAW INTERPRETER RESPONSE =========="
        )
        print(repr(response))
        
        print("===============================================")

        result = self._parse_response(
            response,
        )

        context = result.get("context")

        if (
            isinstance(context, dict)
            and context.get("topic") == "fees"
            and not context.get("fee_type")
            and not session.context.fee_type
        ):
            context["fee_type"] = "admission"

        print(
            f"[INTERPRETER TIMING] LLM call: "
            f"{time.perf_counter() - llm_start:.3f}s"
        )

        if self.DEBUG:

            self._debug(
                request,
                result,
            )

        self._update_request(
            request,
            result,
        )

        # NOTE: user facts (name, semester, hometown, interests) are
        # remembered/recalled by ConversationHandler directly from
        # the session - this keeps that logic in one place instead
        # of duplicating it here.
        self._stage_context(
            request=request,
            result=result,
            session=session,
        )

        return request

    def _stage_context(
        self,
        request: ConversationRequest,
        result: dict[str, object],
        session: ConversationSession,
    ) -> None:
        """
        Work out what ProspectusContext WOULD change to, and hold it
        on request.pending_context rather than writing it straight to
        the session. The caller (ConversationManager / the API layer)
        only calls commit_pending_context() once a prospectus answer
        has actually been produced, so a failed or empty retrieval
        never leaves stale/incorrect context behind.
        """


        request.pending_context = None

        # Only "prospectus" turns are allowed to touch prospectus
        # context. This is a code-level backstop (in addition to the
        # prompt instructions) against a conversational turn ever
        # introducing or implying a department/programme.
        if request.request_type != RequestType.PROSPECTUS:
            return

        context_update = result.get("context")
        context_update = self._validate_context(
            context_update,
            session,
        )

        if not isinstance(context_update, dict):
            return

        new_department = context_update.get("department")
        new_programme = context_update.get("programme")

        # topic_switched = bool(
        #     (new_department and new_department != session.context.department)
        #     or (new_programme and new_programme != session.context.programme)
        # )

        ##change made on 16 oct
        # topic_switched = bool(
        #     not request.is_follow_up
        #     and (
        #         (new_department and new_department != session.context.department)
        #         or (new_programme and new_programme != session.context.programme)
        #         or (
        #             not new_department
        #             and not new_programme
        #             and session.context.department
        #         )
        #         or (
        #             not new_department
        #             and not new_programme
        #             and session.context.programme
        #         )
        #     )
        # )


##change on 18 oct
        # topic_switched = bool(
        #     not request.is_follow_up
        #     and (
        #         (
        #             new_department
        #             and new_department != session.context.department
        #         )
        #         or (
        #             new_programme
        #             and new_programme != session.context.programme
        #         )
        #         or (
        #             not new_department
        #             and not new_programme
        #             and session.context.department
        #         )
        #         or (
        #             not new_department
        #             and not new_programme
        #             and session.context.programme
        #         )
        #         or (
        #             self._normalize_topic(
        #                 context_update.get("topic")
        #             ) == ConversationTopic.PEOPLE
        #             and context_update.get("role")
        #         )
        #     )
        # )
        
        current_topic = self._normalize_topic(
            context_update.get("topic")
        )

        current_role = context_update.get("role")
        previous_role = session.context.person_role

        normalized_current_role = (
            " ".join(current_role.casefold().split())
            if isinstance(current_role, str)
            else ""
        )
        normalized_previous_role = (
            " ".join(previous_role.casefold().split())
            if isinstance(previous_role, str)
            else ""
        )

        role_changed = bool(
            current_topic == ConversationTopic.PEOPLE
            and normalized_current_role
            and normalized_current_role != normalized_previous_role
        )

        topic_switched = bool(
            role_changed
            or (
                not request.is_follow_up
                and (
                    (
                        new_department
                        and new_department != session.context.department
                    )
                    or (
                        new_programme
                        and new_programme != session.context.programme
                    )
                    or (
                        not new_department
                        and not new_programme
                        and session.context.department
                    )
                    or (
                        not new_department
                        and not new_programme
                        and session.context.programme
                    )
                    or (
                        current_topic == ConversationTopic.PEOPLE
                        and current_role
                    )
                )
            )
        )



        admission_code = context_update.get(
            "admission_code"
        )

        request.pending_context = {
            # "topic": self._normalize_topic(
            #     context_update.get("topic"),
            # ),
            "topic": current_topic,
            "department": new_department,
            "programme": new_programme,
            "person_role": context_update.get("role"),
            "admission_code": admission_code,
            "curriculum_programme": context_update.get(
                "curriculum_programme",
            ),
            "curriculum_year": context_update.get(
                "curriculum_year",
            ),
            "curriculum_semester": context_update.get(
                "curriculum_semester",
            ),
            "fee_type": context_update.get("fee_type"),
            "topic_switched": topic_switched,
        }
        # request.pending_context = {
        #     "confidence": result.get(
        #         "confidence",
        #         1.0,
        #     ),
        #     "context": validated_context,
        # }

    def _validate_context(
        self,
        context: dict[str, object],
        session: ConversationSession,
    ) -> dict[str, object]:
        validated = {}

        for key, value in context.items():

            if value is None:
                continue

            if isinstance(value, str):

                value = value.strip()

                if not value:
                    continue

            
            current = getattr(
                session.context,
                key,
                None,
            )

            if (
                current
                and isinstance(value, str)
                and value.casefold() == "general"
            ):
                continue
            if (
                key == "admission_code"
                and not self._is_valid_admission_code(value)
            ):
                continue

            if (
                key == "curriculum_year"
                and not self._is_valid_curriculum_year(value)
            ):
                continue

            if (
                key == "curriculum_semester"
                and not self._is_valid_curriculum_semester(value)
            ):
                continue

            validated[key] = value

        return validated
    def _is_valid_admission_code(
        self,
        value: object,
    ) -> bool:

        if not isinstance(value, str):
            return False

        return bool(
            self.VALID_ADMISSION_CODE.fullmatch(
                value.strip(),
            )
        )


    def _is_valid_curriculum_year(
        self,
        value: object,
    ) -> bool:

        if not isinstance(value, str):
            return False

        return (
            value.strip().casefold()
            in self.VALID_CURRICULUM_YEAR
        )


    def _is_valid_curriculum_semester(
        self,
        value: object,
    ) -> bool:

        if not isinstance(value, str):
            return False

        return (
            value.strip().casefold()
            in self.VALID_CURRICULUM_SEMESTER
        )

    def commit_pending_context(
        self,
        request: ConversationRequest,
        session: ConversationSession,
    ) -> None:
        """
        Apply the ProspectusContext changes staged by _stage_context()
        to the session. Call this ONLY after a prospectus answer has
        actually been produced (e.g. AnswerService returned a real
        answer, not an error/empty result) - that's what keeps
        ProspectusContext clean when retrieval comes up empty.
        """

        pending = request.pending_context

        if not pending:
            return

        if pending.get("topic_switched"):

            # A different department/programme is now in focus -
            # drop role/admission/curriculum/fee details that were
            # scoped to the previous one.
            self._reset_scoped_context(
                session,
            )

        # ProspectusContext.update() only overwrites fields with a
        # non-None value and silently keeps the previous value
        # otherwise, so unmentioned fields are preserved automatically.
        session.context.update(
            topic=pending.get("topic"),
            department=pending.get("department"),
            programme=pending.get("programme"),
            person_role=pending.get("person_role"),
            admission_code=pending.get("admission_code"),
            curriculum_programme=pending.get("curriculum_programme"),
            curriculum_year=pending.get("curriculum_year"),
            curriculum_semester=pending.get("curriculum_semester"),
            fee_type=pending.get("fee_type"),
        )

        request.pending_context = None

    def _reset_scoped_context(
        self,
        session: ConversationSession,
    ) -> None:

        for field_name in self.SCOPED_CONTEXT_FIELDS:

            setattr(
                session.context,
                field_name,
                None,
            )

    def _normalize_topic(
        self,
        value: object,
    ) -> ConversationTopic | None:

        if not value:
            return None

        try:

            return ConversationTopic(
                str(value).strip().lower(),
            )

        except ValueError:

            return None


    def _update_request(
        self,
        request: ConversationRequest,
        result: dict[str, object],
    ) -> None:

        try:

            request.request_type = RequestType(
                result.get(
                    "request_type",
                    "gibberish",
                )
            )

        except ValueError:

            request.request_type = (
                RequestType.GIBBERISH
            )

        request.rewritten_query = (
            result.get(
                "rewritten_query",
                request.rewritten_query,
            )
        )

        confidence = float(
            result.get(
                "confidence",
                0.0,
            )
        )

        request.confidence = max(
            0.0,
            min(
                confidence,
                1.0,
            ),
        )

        request.is_follow_up = bool(
            result.get(
                "is_follow_up",
                False,
            )
        )

        request.needs_clarification = bool(
            result.get(
                "needs_clarification",
                False,
            )
        )

        request.clarification_question = (
            result.get(
                "clarification_question",
            )
        )

        request.llm_reasoning = None

    def _build_prompt(
        self,
        request: ConversationRequest,
        session: ConversationSession,
    ) -> str:

        state = request.state
        context = session.context

        summary = (
            state.chat_summary
            or "None"
        )

        topic = (
            context.topic.value
            if context.topic
            else "None"
        )

        department = (
            context.department
            or "None"
        )

        programme = (
            context.programme
            or "None"
        )

        role = (
            context.person_role
            or "None"
        )

        admission_code = (
            context.admission_code
            or "None"
        )

        curriculum_programme = (
            context.curriculum_programme
            or "None"
        )

        curriculum_year = (
            context.curriculum_year
            or "None"
        )

        curriculum_semester = (
            context.curriculum_semester
            or "None"
        )

        fee_type = (
            context.fee_type
            or "None"
        )

        # Short-term hybrid context: the last few turns of THIS chat,
        # kept on the session (not the persisted chat history), so
        # follow-ups like "Co-chairperson?" can be read in context.


        #changes made 15 oct
        recent_messages = (
            "\n".join(
                f"{message['role']}: {message['content']}"
                for message in session.get_messages()
            )
            or "No previous conversation."
        )
        # Short-term conversation history
        # messages = session.get_messages()
        # recent_start = max(0, len(messages) - 4)
        # formatted_messages = []

        # for index, message in enumerate(messages):
        #     role = message["role"]
        #     content = message["content"]

        #     if role == "assistant" and index < recent_start:
        #         max_chars = 400
        #         if len(content) > max_chars:
        #             content = content[:max_chars].rstrip() + "..."

        #     formatted_messages.append(
        #         f"{role}: {content}"
        #     )

        # recent_messages = (
        #     "\n".join(formatted_messages)
        #     or "No previous conversation."
        # )


        return f"""

        Conversation Summary:

        {summary}

        Current Topic:

        {topic}

        Current Department:

        {department}

        Current Programme:

        {programme}

        Current Role In Focus:

        {role}

        Current Admission Code:

        {admission_code}

        Current Curriculum Programme:

        {curriculum_programme}

        Current Curriculum Year:

        {curriculum_year}

        Current Curriculum Semester:

        {curriculum_semester}

        Current Fee Type:

        {fee_type}

        Recent Conversation:

        {recent_messages}

        Current User Query:

        {request.rewritten_query}

        Use the conversation summary, recent conversation, and the
        current prospectus context above to resolve follow-up
        questions.

        If the user changes the topic to a different department or
        programme, treat it as a topic switch: use the new one and
        do not keep mixing in details from the one discussed before.

        If the query is ambiguous, set
        "needs_clarification" to true and provide an
        appropriate "clarification_question".

        If the query is unrelated to the university
        prospectus, classify it as "irrelevant".

        If the query is meaningless or cannot be
        interpreted, classify it as "gibberish".

        Correct only obvious spelling mistakes that preserve the user's intended meaning. Do not invent missing information.

        Rewrite the query as a complete standalone
        question.

        Return ONLY valid JSON, matching the "context" object rules
        described in the system prompt.

        """

    def _parse_response(
        self,
        response: str,
    ) -> dict[str, object]:

        response = response.strip()

        if "```" in response:

            response = (
                response
                    .replace("```json", "")
                    .replace("```", "")
                    .strip()
            )

        try:

            return json.loads(
                response,
            )

        except Exception:

            return {

                "request_type": "gibberish",

                "rewritten_query": "",

                "confidence": 0.0,

                "is_follow_up": False,

                "needs_clarification": True,

                "clarification_question": (
                    "Could you rephrase your question?"
                ),

                "llm_reasoning": (
                    "Failed to parse interpreter response."
                ),

                "context": {},
            }
    def _debug(
        self,
        request: ConversationRequest,
        result: dict[str, object],
    ) -> None:

        print()
        print("=" * 80)
        print("QUERY INTERPRETER")
        print("=" * 80)

        print("Original Query:")
        print(request.original_query)
        print()

        print("Rewritten Query:")
        print(result.get("rewritten_query"))
        print()

        print("Request Type:")
        print(result.get("request_type"))
        print()

        print("Confidence:")
        print(result.get("confidence"))
        print()

        print("Follow Up:")
        print(result.get("is_follow_up"))
        print()

        print("Needs Clarification:")
        print(result.get("needs_clarification"))
        print()

        print("Clarification Question:")
        print(result.get("clarification_question"))
        print()

        print("Context:")
        print(result.get("context"))
        print()

        print("Reasoning:")
        print(result.get("llm_reasoning"))
        print()

        print("Raw JSON:")
        print(
            json.dumps(
                result,
                indent=4,
            )
        )

        print()