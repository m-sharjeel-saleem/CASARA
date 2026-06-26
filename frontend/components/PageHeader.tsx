export function PageHeader({ eyebrow, title, children }: {
  eyebrow: string; title: React.ReactNode; children?: React.ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <div className="eyebrow mb-1.5">{eyebrow}</div>
        <h1 className="font-display text-2xl font-bold tracking-tight text-white sm:text-[28px]">{title}</h1>
      </div>
      {children && <div className="flex items-center gap-2">{children}</div>}
    </div>
  );
}
