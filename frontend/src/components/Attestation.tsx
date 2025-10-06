"use client";

export default function Attestation({
  checked,
  setChecked,
}: {
  checked: boolean;
  setChecked: (v: boolean) => void;
}) {
  return (
    <label className="flex items-start gap-2 text-sm">
      <input
        type="checkbox"
        className="mt-1"
        checked={checked}
        onChange={(e) => setChecked(e.target.checked)}
      />
      <span>
        I own or am explicitly authorized to test this domain. I understand this tool performs only
        safe, unauthenticated checks.
      </span>
    </label>
  );
}
