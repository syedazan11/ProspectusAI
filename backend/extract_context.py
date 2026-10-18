from pathlib import Path

text = Path(r"/mnt/data/Pasted text(20260903-173530).txt").read_text(encoding="utf-8")

start = text.index("========== FINAL LLM CONTEXT ==========") + len("========== FINAL LLM CONTEXT ==========")
end = text.index("========================================", start)

context = text[start:end].strip()

Path("real_context.txt").write_text(context, encoding="utf-8")

print("CONTEXT CHARS:", len(context))
