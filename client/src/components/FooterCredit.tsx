export default function FooterCredit() {
  return (
    <footer className="fixed bottom-16 left-0 right-0 z-40 bg-gray-50 border-t border-gray-100 py-2">
      <p className="text-center text-xs text-gray-400 tracking-wide">
        dev by:{' '}
        <a
          href="mailto:nativecodesdevelopers@gmail.com"
          className="text-gray-500 hover:text-green-600 transition-colors"
        >
          nativecodesdevelopers@gmail.com
        </a>
      </p>
    </footer>
  );
}
