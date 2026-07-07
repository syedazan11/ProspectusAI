const EXAMPLES = [
  "How many Computer Science seats are available in SF-1(a)?",
  "What is the eligibility criteria for admission?",
  "What are the tuition fees for the Engineering programme?",
  "Is there a hostel facility for first-year students?",
];

interface ExampleChipsProps {
  onSelect: (question: string) => void;
  disabled?: boolean;
}

export function ExampleChips({ onSelect, disabled }: ExampleChipsProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {EXAMPLES.map((question) => (
        <button
          key={question}
          type="button"
          disabled={disabled}
          onClick={() => onSelect(question)}
          className="rounded-full border border-brand-blue/20 bg-white px-3.5 py-1.5 text-left text-sm text-slate-600 shadow-sm transition-all hover:-translate-y-0.5 hover:border-brand-blue/40 hover:text-brand-blue hover:shadow-soft disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0"
        >
          {question}
        </button>
      ))}
    </div>
  );
}
