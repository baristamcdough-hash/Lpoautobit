export default function FooterCredit() {
  return (
    <footer className="fixed bottom-16 left-0 right-0 z-40 bg-slate-50 border-t border-slate-200 py-2">
      <p className="text-center text-xs text-slate-400 tracking-wide">
        dev by:{' '}
        <a
          href="mailto:nativecodesdevelopers@gmail.com"
          className="text-slate-500 hover:text-teal-600 transition-colors"
        >
          nativecodesdevelopers@gmail.com
        </a>
      </p>
    </footer>
  );
}
