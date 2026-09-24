import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Aether · Core Console",
  description:
    "Aether Core console — Telegram bridge · Ollama · one-time setup (9Router-style shell)",
};

const themeBootstrap = `(function(){try{var t=localStorage.getItem('aether-theme');if(t!=='light')document.documentElement.classList.add('dark');}catch(e){}})();`;

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeBootstrap }} />
      </head>
      <body>{children}</body>
    </html>
  );
}