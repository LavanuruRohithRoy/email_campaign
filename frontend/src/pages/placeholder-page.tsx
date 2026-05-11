export function PlaceholderPage({ title }: { title: string }) {
  return (
    <section className="grid gap-2">
      <h2 className="text-2xl font-semibold tracking-normal">{title}</h2>
      <p className="text-sm text-muted-foreground">This area will continue in the next module.</p>
    </section>
  );
}
