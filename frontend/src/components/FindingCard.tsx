import { Finding } from "@/types";
import StatusBadge from "./StatusBadge";

export default function FindingCard({ f }: { f: Finding }) {
  return (
    <div className="border rounded-xl p-4 shadow-sm bg-white">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">{f.title}</h3>
        <StatusBadge status={f.status} />
      </div>
      <div className="mt-1 text-xs text-gray-500">
        Risk: {f.risk} • Confidence: {f.confidence}
      </div>
      <div className="mt-3">
        <h4 className="text-sm font-medium">Evidence</h4>
        <pre className="mt-1 text-xs bg-gray-50 p-2 rounded overflow-x-auto">
{JSON.stringify(f.evidence, null, 2)}
        </pre>
      </div>
      <div className="mt-3">
        <h4 className="text-sm font-medium">Recommendation</h4>
        <pre className="mt-1 text-xs bg-gray-50 p-2 rounded overflow-x-auto whitespace-pre-wrap">
{f.recommendation}
        </pre>
      </div>
    </div>
  );
}
