"use client";

// The welcome card: shown once on a first visit, and again from the header's "How it works" button.
// The numbers come from the data in use, so they never go out of date.
export default function Onboarding({
  mode,
  isolates,
  regions,
  designed,
  onTry,
  onClose,
}: {
  mode: "first" | "help";
  isolates: number;
  regions: string[];
  designed: number;
  onTry: () => void;
  onClose: () => void;
}) {
  const steps = [
    {
      n: "1",
      title: "Ask",
      body: `Use the chat in your own words, for example "Which rifampicin resistance mutations are common in ${regions[0] ?? "Bandung"}?" A drug, gene or patient scenario works too.`,
    },
    {
      n: "2",
      title: "Or pick",
      body: `Open the Target library, choose a region to see which resistance variants occur there and how often, then pick up to 6 of the ${designed} variants that have a design.`,
    },
    {
      n: "3",
      title: "Read",
      body: `Results show, for each variant, how many isolates carry it in each region, then rank the assay and show its primers, probes and how many of the ${isolates} isolates it matches.`,
    },
  ];
  return (
    <section aria-label="Welcome" className="rounded-2xl border border-accent bg-surface px-5 py-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">{mode === "first" ? "Welcome to ResistTB" : "How ResistTB works"}</h2>
          <p className="mt-0.5 text-sm text-muted">Find which drug-resistance mutations occur in each region, and get qPCR primers and probes designed for them, from real genomes.</p>
        </div>
        <button type="button" onClick={onClose} aria-label="Close the welcome card" className="rounded-md px-2 py-1 text-xs text-muted hover:text-ink">
          Close
        </button>
      </div>

      <ol className="mt-4 grid gap-3 sm:grid-cols-3">
        {steps.map((s) => (
          <li key={s.n} className="rounded-xl border border-line bg-bg px-3.5 py-3">
            <div className="flex items-center gap-2">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-accent text-xs font-medium text-surface">{s.n}</span>
              <span className="text-sm font-medium">{s.title}</span>
            </div>
            <p className="mt-1.5 text-xs leading-5 text-muted">{s.body}</p>
          </li>
        ))}
      </ol>

      <div className="mt-4 rounded-xl border border-line bg-warn-soft px-3.5 py-3 text-xs leading-5 text-warn">
        <div className="font-medium">Good to know</div>
        <ul className="mt-1 list-disc space-y-0.5 pl-4">
          <li>Everything is computed on a computer. Nothing has been tested in a tube.</li>
          <li>Coverage is measured on the same isolates the oligos were designed on, so it is optimistic.</li>
          <li>Your chats and their reports are saved in this browser only.</li>
        </ul>
      </div>

      <details className="mt-3 text-xs">
        <summary className="cursor-pointer text-muted hover:text-ink">How to read the results</summary>
        <dl className="mt-2 grid gap-x-4 gap-y-1.5 leading-5 sm:grid-cols-[10rem_1fr]">
          <dt className="font-medium">Overall score</dt>
          <dd className="text-muted">0 to 100: 30% how conserved the sites are, 30% how well the oligos behave thermodynamically, 20% specificity, 20% WHO evidence for the mutation.</dd>
          <dt className="font-medium">Exact match</dt>
          <dd className="text-muted">Isolates that match every primer and probe base. &ldquo;One mismatch&rdquo; (not at a primer&rsquo;s 3&prime; end) should still work. &ldquo;Likely to fail&rdquo; means two or more mismatches, or one in the last 3 bases of a primer.</dd>
          <dt className="font-medium">Wild-type and mutant probe</dt>
          <dd className="text-muted">The mutant probe signalling means that resistance variant is present. The wild-type probe alone means that site is unchanged, which is not proof of susceptibility.</dd>
          <dt className="font-medium">Tm gap</dt>
          <dd className="text-muted">The estimated melting-temperature drop when a probe meets the other allele. Larger separates the alleles better.</dd>
          <dt className="font-medium">Tubes</dt>
          <dd className="text-muted">Assays grouped to share a tube on a 4-channel instrument, two per tube, checked for primer dimers. A model, not a test.</dd>
        </dl>
      </details>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button type="button" onClick={onTry} className="rounded-lg bg-accent px-3 py-1.5 text-sm font-medium text-surface">
          Try an example
        </button>
        <button type="button" onClick={onClose} className="rounded-lg border border-line px-3 py-1.5 text-sm hover:border-accent">
          {mode === "first" ? "Got it" : "Close"}
        </button>
      </div>
    </section>
  );
}
