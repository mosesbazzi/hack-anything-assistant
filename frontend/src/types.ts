export type Status = "PASS" | "WARN" | "FAIL" | "INFO";

export interface Finding {
  id: string;
  key: string;
  title: string;
  status: Status;
  risk: "low" | "medium" | "high";
  confidence: "low" | "medium" | "high";
  evidence: Record<string, any>;
  recommendation: string;
}

export interface Scan {
  id: string;
  url: string;
  score: number;
  findings: Finding[];
}
