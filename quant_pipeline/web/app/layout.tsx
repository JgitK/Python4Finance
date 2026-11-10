import type { Metadata, Viewport } from "next";
import { Cascadia_Code } from "next/font/google";
import "./globals.css";

// Cascadia Code for headings, labels, numbers and buttons. It is a
// variable font, so no weight is necessary. Body text stays system-ui.
const cascadia = Cascadia_Code({
  variable: "--font-mono",
  subsets: ["latin"],
  style: ["normal", "italic"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Which eggs, and how many? A walk through Markowitz",
  description:
    "A scrollytelling walk through Markowitz portfolio theory with real S&P 500 data: pick stocks, read the timing, search ten thousand portfolios, and put the money in.",
};

export const viewport: Viewport = {
  themeColor: "#F9F9F9",
  colorScheme: "light",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={cascadia.variable}>
      <body>{children}</body>
    </html>
  );
}
