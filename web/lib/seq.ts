export function gcPercent(seq: string): number {
  if (!seq) return 0;
  const gc = [...seq.toUpperCase()].filter((b) => b === "G" || b === "C").length;
  return (gc / seq.length) * 100;
}

export function formatPos(n: number): string {
  return n.toLocaleString("en-US");
}
