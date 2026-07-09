$ErrorActionPreference = "Stop"

$Path = ".\\src\\generation\\answer_service.py"
if (-not (Test-Path $Path)) { throw "Run this from the backend folder. File not found: $Path" }

$Text = Get-Content $Path -Raw

$Old = @'
        prompt = self._build_prompt(
            question=retrieval_query,
            context=context,
            has_complex_table=(
                has_complex_table
            ),
        )
'@
$New = @'
        prompt = self._build_prompt(
            question=question,
            context=context,
            has_complex_table=(
                has_complex_table
            ),
            conversation_history=recent_history,
        )
'@
if (-not $Text.Contains($Old)) { throw "Expected prompt block was not found. No file changed." }
$Text = $Text.Replace($Old, $New)

$Old2 = @'
        table_instruction = ""

        if has_complex_table:
'@
$New2 = @'
        history_lines = []

        for message in (
            conversation_history or []
        )[-4:]:
            role = str(
                message.get("role", "")
            ).strip()

            content = str(
                message.get("content", "")
            ).strip()[:400]

            if role in {"user", "assistant"} and content:
                history_lines.append(
                    f"{role.title()}: {content}"
                )

        conversation_context = (
            "\n".join(history_lines)
            if history_lines
            else "No previous conversation."
        )

        table_instruction = ""

        if has_complex_table:
'@
if (-not $Text.Contains($Old2)) { throw "Expected _build_prompt block was not found. No file changed." }
$Text = $Text.Replace($Old2, $New2)

$Old3 = @'
The uploaded prospectus is the only source of truth.

Rules:
'@
$New3 = @'
The uploaded prospectus is the only source of truth.

RECENT CONVERSATION:

{conversation_context}

Rules:
- Use the recent conversation only to resolve what the
  user's current question refers to.
- Answer the current user question, not an earlier one.
'@
if (-not $Text.Contains($Old3)) { throw "Expected prompt rules block was not found. No file changed." }
$Text = $Text.Replace($Old3, $New3)

Set-Content $Path $Text -Encoding utf8
python -m py_compile $Path
Write-Host "UPDATED: answer_service.py"
Write-Host "COMPILE: passed"
