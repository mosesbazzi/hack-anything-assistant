import { Status } from "@/types";

export default function StatusBadge({ status }: { status: Status }) {
  const classes: Record<Status, string> = {
    PASS: "bg-green-100 text-green-800",
    WARN: "bg-yellow-100 text-yellow-800",
    FAIL: "bg-red-100 text-red-800",
    INFO: "bg-blue-100 text-blue-800",
  };
  return <span className={`px-2 py-1 text-xs rounded ${classes[status]}`}>{status}</span>;
}
