export function Footer() {
  return (
    <footer className="border-t border-slate-200 py-6 mt-auto">
      <div className="max-w-4xl mx-auto px-4 flex flex-wrap gap-x-6 gap-y-2 text-sm text-slate-600">
        <a href="/privacy" className="hover:text-slate-900">
          Privacy
        </a>
        <a href="/terms" className="hover:text-slate-900">
          Terms
        </a>
        <a href="/imprint" className="hover:text-slate-900">
          Imprint
        </a>
      </div>
    </footer>
  );
}
