'use client';

import type { ReactNode } from 'react';

type PageHeaderProps = {
  sectionLabel: string;
  title: string;
  rightSlot?: ReactNode;
  containerWidthClassName?: string;
};

export function PageHeader({
  sectionLabel,
  title,
  rightSlot,
  containerWidthClassName = 'max-w-6xl',
}: PageHeaderProps) {
  return (
    <header className="border-b border-slate-800">
      <div
        className={`${containerWidthClassName} mx-auto px-4 py-4 flex items-center justify-between`}
      >
        <div>
          <div className="text-xs uppercase tracking-wide text-slate-500">
            {sectionLabel}
          </div>
          <h1 className="text-xl font-semibold">{title}</h1>
        </div>
        {rightSlot && <div className="flex items-center gap-3">{rightSlot}</div>}
      </div>
    </header>
  );
}


