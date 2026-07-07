import { PROCESSING_STAGES, type ProcessingStage } from "../../types/admin";

interface ProcessingStagesProps {
  currentStage: ProcessingStage | null;
}

export function ProcessingStages({ currentStage }: ProcessingStagesProps) {
  const currentIndex = currentStage
    ? PROCESSING_STAGES.indexOf(currentStage)
    : -1;

  return (
    <div className="rounded-2xl border border-white bg-white/90 p-5 shadow-card">
      <h3 className="mb-4 font-display text-sm font-semibold text-slate-800">
        Processing pipeline
      </h3>

      <ol className="space-y-0">
        {PROCESSING_STAGES.map((stage, index) => {
          const isDone = currentIndex >= 0 && index < currentIndex;
          const isCurrent = index === currentIndex;
          const isPending = !isDone && !isCurrent;

          return (
            <li key={stage} className="flex gap-3">
              <div className="flex flex-col items-center">
                <span
                  className={`grid h-6 w-6 shrink-0 place-items-center rounded-full text-[11px] font-bold ${
                    isDone
                      ? "bg-brand-teal text-white"
                      : isCurrent
                        ? "bg-brand-gradient text-white"
                        : "bg-slate-100 text-slate-400"
                  }`}
                >
                  {isDone ? "✓" : index + 1}
                </span>
                {index < PROCESSING_STAGES.length - 1 && (
                  <span
                    className={`my-0.5 h-6 w-0.5 rounded-full ${
                      isDone ? "bg-brand-teal/50" : "bg-slate-100"
                    }`}
                  />
                )}
              </div>
              <div className="pb-5">
                <p
                  className={`text-sm font-medium ${
                    isPending ? "text-slate-400" : "text-slate-700"
                  }`}
                >
                  {stage}
                </p>
                {isCurrent && (
                  <p className="text-xs text-brand-purple">In progress…</p>
                )}
              </div>
            </li>
          );
        })}
      </ol>

      {currentIndex === -1 && (
        <p className="rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-500">
          No document is currently being processed.
        </p>
      )}
    </div>
  );
}
