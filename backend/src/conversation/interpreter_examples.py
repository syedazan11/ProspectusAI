from __future__ import annotations

FEW_SHOT_EXAMPLES = """
User:
Computer Science

Output:
{
    "request_type": "prospectus",
    "rewritten_query": "Computer Science",
    "confidence": 0.99,
    "is_follow_up": false,
    "needs_clarification": true,
    "clarification_question": "What would you like to know about Computer Science?",
    "llm_reasoning": "The user only mentioned a programme name without asking a question.",
    "context": {
        "topic": "general",
        "department": "Computer Science",
        "programme": null,
        "role": null,
        "admission_code": null,
        "curriculum_programme": null,
        "curriculum_year": null,
        "curriculum_semester": null,
        "fee_type": null
    }
}

User:
Chairperson of Electronic Engineering

Output:
{
    "request_type": "prospectus",
    "rewritten_query": "Who is the chairperson of the Electronic Engineering department?",
    "confidence": 0.99,
    "is_follow_up": false,
    "needs_clarification": false,
    "clarification_question": null,
    "llm_reasoning": "The user asked who holds a specific role in a specific department.",
    "context": {
        "topic": "people",
        "department": "Electronic Engineering",
        "programme": null,
        "role": "chairperson",
        "admission_code": null,
        "curriculum_programme": null,
        "curriculum_year": null,
        "curriculum_semester": null,
        "fee_type": null
    }
}

Current Topic: people
Current Department: Electronic Engineering
Current Role In Focus: chairperson

User:
Co-chairperson?

Output:
{
    "request_type": "prospectus",
    "rewritten_query": "Who is the co-chairperson of the Electronic Engineering department?",
    "confidence": 0.98,
    "is_follow_up": true,
    "needs_clarification": false,
    "clarification_question": null,
    "llm_reasoning": "The user asked about a related role in the same department already in focus.",
    "context": {
        "topic": "people",
        "department": null,
        "programme": null,
        "role": "co-chairperson",
        "admission_code": null,
        "curriculum_programme": null,
        "curriculum_year": null,
        "curriculum_semester": null,
        "fee_type": null
    }
}

Current Department: Computer Science

User:
Hostel?

Output:
{
    "request_type": "prospectus",
    "rewritten_query": "What hostel facilities are available for Computer Science students?",
    "confidence": 0.95,
    "is_follow_up": true,
    "needs_clarification": false,
    "clarification_question": null,
    "llm_reasoning": "The user is now asking about hostel information for the department already in focus.",
    "context": {
        "topic": "hostel",
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

User:
weather today

Output:
{
    "request_type": "irrelevant",
    "rewritten_query": "weather today",
    "confidence": 1.0,
    "is_follow_up": false,
    "needs_clarification": false,
    "clarification_question": null,
    "llm_reasoning": "The query is unrelated to the university prospectus.",
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

User:
asdfghjkl

Output:
{
    "request_type": "gibberish",
    "rewritten_query": "asdfghjkl",
    "confidence": 1.0,
    "is_follow_up": false,
    "needs_clarification": true,
    "clarification_question": "Could you rephrase your question?",
    "llm_reasoning": "The input appears to be meaningless.",
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

User:
Hi

Output:
{
    "request_type": "greeting",
    "rewritten_query": "Hi",
    "confidence": 1.0,
    "is_follow_up": false,
    "needs_clarification": false,
    "clarification_question": null,
    "llm_reasoning": "The user greeted the assistant.",
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

User:
My name is Azan

Output:
{
    "request_type": "conversation",
    "rewritten_query": "My name is Azan.",
    "confidence": 1.0,
    "is_follow_up": false,
    "needs_clarification": false,
    "clarification_question": null,
    "llm_reasoning": "The user is sharing personal information, not asking about the prospectus.",
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

User:
What's my name?

Output:
{
    "request_type": "conversation",
    "rewritten_query": "What is my name?",
    "confidence": 1.0,
    "is_follow_up": true,
    "needs_clarification": false,
    "clarification_question": null,
    "llm_reasoning": "The user is asking the assistant to recall previously shared personal information.",
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

User:
What can you do?

Output:
{
    "request_type": "system",
    "rewritten_query": "What can you do?",
    "confidence": 1.0,
    "is_follow_up": false,
    "needs_clarification": false,
    "clarification_question": null,
    "llm_reasoning": "The user is asking about the assistant.",
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

User:
Tell me about R-1(A)

Output:
{
    "request_type": "prospectus",
    "rewritten_query": "Tell me about admission category R-1(A).",
    "confidence": 0.99,
    "is_follow_up": false,
    "needs_clarification": false,
    "clarification_question": null,
    "llm_reasoning": "Recognized an official admission category.",
    "context": {
        "topic": "admission",
        "department": null,
        "programme": null,
        "role": null,
        "admission_code": "R-1(A)",
        "curriculum_programme": null,
        "curriculum_year": null,
        "curriculum_semester": null,
        "fee_type": null
    }
}

Current Topic: admission
Current Admission Code: R-1(A)

User:
Eligibility?

Output:
{
    "request_type": "prospectus",
    "rewritten_query": "What is the eligibility criteria for admission category R-1(A)?",
    "confidence": 0.98,
    "is_follow_up": true,
    "needs_clarification": false,
    "clarification_question": null,
    "llm_reasoning": "Resolved the follow-up using the admission code already in focus.",
    "context": {
        "topic": "admission",
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

Current Topic: admission
Current Admission Code: R-1(A)

User:
Required documents?

Output:
{
    "request_type": "prospectus",
    "rewritten_query": "What documents are required for admission category R-1(A)?",
    "confidence": 0.98,
    "is_follow_up": true,
    "needs_clarification": false,
    "clarification_question": null,
    "llm_reasoning": "Resolved the follow-up using the admission code already in focus.",
    "context": {
        "topic": "admission",
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

User:
Computer Science curriculum

Output:
{
    "request_type": "prospectus",
    "rewritten_query": "What is the curriculum for Computer Science?",
    "confidence": 0.98,
    "is_follow_up": false,
    "needs_clarification": false,
    "clarification_question": null,
    "llm_reasoning": "The user asked about the curriculum for a specific programme.",
    "context": {
        "topic": "curriculum",
        "department": null,
        "programme": "Computer Science",
        "role": null,
        "admission_code": null,
        "curriculum_programme": "Computer Science",
        "curriculum_year": null,
        "curriculum_semester": null,
        "fee_type": null
    }
}

Current Topic: curriculum
Current Curriculum Programme: Computer Science

User:
Second year

Output:
{
    "request_type": "prospectus",
    "rewritten_query": "What is the second year curriculum for Computer Science?",
    "confidence": 0.97,
    "is_follow_up": true,
    "needs_clarification": false,
    "clarification_question": null,
    "llm_reasoning": "Resolved the follow-up using the curriculum programme already in focus.",
    "context": {
        "topic": "curriculum",
        "department": null,
        "programme": null,
        "role": null,
        "admission_code": null,
        "curriculum_programme": null,
        "curriculum_year": "second year",
        "curriculum_semester": null,
        "fee_type": null
    }
}

Current Topic: curriculum
Current Curriculum Programme: Computer Science
Current Curriculum Year: second year

User:
Which courses have labs?

Output:
{
    "request_type": "prospectus",
    "rewritten_query": "Which second year Computer Science courses have labs?",
    "confidence": 0.96,
    "is_follow_up": true,
    "needs_clarification": false,
    "clarification_question": null,
    "llm_reasoning": "Resolved the follow-up using the curriculum programme and year already in focus.",
    "context": {
        "topic": "curriculum",
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

Current Department: Computer Science

User:
Civil Engineering

Output:
{
    "request_type": "prospectus",
    "rewritten_query": "Civil Engineering",
    "confidence": 0.9,
    "is_follow_up": false,
    "needs_clarification": true,
    "clarification_question": "What would you like to know about Civil Engineering?",
    "llm_reasoning": "The user switched to a different department without asking a specific question yet.",
    "context": {
        "topic": "general",
        "department": "Civil Engineering",
        "programme": null,
        "role": null,
        "admission_code": null,
        "curriculum_programme": null,
        "curriculum_year": null,
        "curriculum_semester": null,
        "fee_type": null
    }
}

Current Department: Civil Engineering

User:
Who is the chairperson?

Output:
{
    "request_type": "prospectus",
    "rewritten_query": "Who is the chairperson of the Civil Engineering department?",
    "confidence": 0.98,
    "is_follow_up": true,
    "needs_clarification": false,
    "clarification_question": null,
    "llm_reasoning": "Resolved the follow-up using the department already in focus after the topic switch.",
    "context": {
        "topic": "people",
        "department": null,
        "programme": null,
        "role": "chairperson",
        "admission_code": null,
        "curriculum_programme": null,
        "curriculum_year": null,
        "curriculum_semester": null,
        "fee_type": null
    }
}

User:
ABC department

Output:
{
    "request_type": "prospectus",
    "rewritten_query": "ABC department",
    "confidence": 0.55,
    "is_follow_up": false,
    "needs_clarification": true,
    "clarification_question": "Could you clarify what 'ABC' refers to?",
    "llm_reasoning": "The abbreviation could not be resolved confidently.",
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

Current Department: Computer Science

User:
Eligibility?

Output:
{
    "request_type": "prospectus",
    "rewritten_query": "What are the eligibility requirements for Computer Science?",
    "confidence": 0.99,
    "is_follow_up": true,
    "needs_clarification": false,
    "clarification_question": null,
    "llm_reasoning": "Resolved the follow-up using the previous topic.",
    "context": {
        "topic": "admission",
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

Current Topic: None
Current Department: None
Current Programme: None
Current Admission Code: None
Current Curriculum Programme: None

User:
Eligibility?

Output:
{
    "request_type": "prospectus",
    "rewritten_query": "Eligibility?",
    "confidence": 0.4,
    "is_follow_up": false,
    "needs_clarification": true,
    "clarification_question": "Eligibility for which programme or admission category would you like to know about?",
    "llm_reasoning": "The user asked a short follow-up question, but no department, programme, or admission code is currently in focus to resolve it against.",
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

"""