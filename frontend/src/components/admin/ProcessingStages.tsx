import {
  PROCESSING_STAGES,
  type ProcessingStage,
} from "../../types/admin";

interface ProcessingStagesProps {
  currentStage: ProcessingStage | null;
}

export function ProcessingStages({
  currentStage,
}: ProcessingStagesProps) {
  const currentIndex = currentStage
    ? PROCESSING_STAGES.indexOf(currentStage)
    : -1;

  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-md">
      <div className="mb-6">
        <h3 className="text-lg font-bold text-[#163A6B]">
          Processing Pipeline
        </h3>

        <p className="mt-1 text-sm text-slate-500">
          Current document processing progress
        </p>
      </div>

      <ol className="space-y-5">
        {PROCESSING_STAGES.map((stage, index) => {
          const isDone =
            currentIndex >= 0 &&
            index < currentIndex;

          const isCurrent =
            index === currentIndex;

          const isPending =
            !isDone && !isCurrent;

          return (
            <li
              key={stage}
              className="flex gap-4"
            >
              {/* Timeline */}
              <div className="flex flex-col items-center">
                <div
                  className={`flex h-10 w-10 items-center justify-center rounded-full text-sm font-bold transition-all ${
                    isDone
                      ? "bg-green-600 text-white"
                      : isCurrent
                      ? "bg-[#163A6B] text-white shadow-lg"
                      : "bg-slate-100 text-slate-400"
                  }`}
                >
                  {isDone ? "✓" : index + 1}
                </div>

                {index <
                  PROCESSING_STAGES.length - 1 && (
                  <div
                    className={`mt-2 h-10 w-1 rounded-full ${
                      isDone
                        ? "bg-green-400"
                        : "bg-slate-200"
                    }`}
                  />
                )}
              </div>

              {/* Stage Details */}
              <div className="flex-1 pb-2">
                <h4
                  className={`text-base font-semibold ${
                    isPending
                      ? "text-slate-400"
                      : "text-slate-800"
                  }`}
                >
                  {stage}
                </h4>

                {isDone && (
                  <p className="mt-1 text-sm text-green-600">
                    ✓ Completed
                  </p>
                )}

                {isCurrent && (
                  <p className="mt-1 text-sm font-medium text-[#163A6B]">
                    ⚙ Processing...
                  </p>
                )}

                {isPending && (
                  <p className="mt-1 text-sm text-slate-400">
                    Waiting
                  </p>
                )}
              </div>
            </li>
          );
        })}
      </ol>

      {currentIndex === -1 && (
        <div className="mt-6 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-5 text-center">
          <div className="mb-2 text-3xl">
            📄
          </div>

          <p className="font-medium text-slate-700">
            No document is currently being processed.
          </p>

          <p className="mt-1 text-sm text-slate-500">
            Upload a prospectus to begin the processing pipeline.
          </p>
        </div>
      )}
    </div>
  );
}