import { Finding } from "@/types";
import StatusBadge from "./StatusBadge";

export default function FindingCard({ f }: { f: Finding }) {
  return (
    <div className="rounded-2xl border border-slate-200/70 bg-white/90 p-4 text-slate-900
    +               shadow-sm ring-1 ring-slate-900/5 transition-shadow hover:shadow-md">
      <div className="flex items-center justify-between border-b border-slate-100 pb-2 mb-3">
        <h3 className="font-semibold text-slate-900">{f.title}</h3>
        <StatusBadge status={f.status} />
      </div>
      <div className="mt-1 text-xs text-slate-500">
        Risk: {f.risk} • Confidence: {f.confidence}
      </div>
      <div className="mt-3">
        <h4 className="text-sm font-medium text-slate-800">Evidence</h4>
        <pre className="mt-1 text-xs bg-slate-50/80 border border-slate-200 rounded-lg p-2 overflow-x-auto">
{JSON.stringify(f.evidence, null, 2)}
        </pre>
      </div>
      <div className="mt-3">
        <h4 className="text-sm font-medium text-slate-800">Recommendation</h4>
        <pre className="mt-1 text-xs bg-slate-50/80 border border-slate-200 rounded-lg p-2 overflow-x-auto whitespace-pre-wrap">
{f.recommendation}
        </pre>
      </div>
    </div>
  );
}
