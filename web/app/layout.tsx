import type { Metadata } from "next";
import { Inter, Noto_Sans_Devanagari } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const devanagari = Noto_Sans_Devanagari({
  variable: "--font-devanagari",
  subsets: ["devanagari"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Visarjan Ghat Watch — Bhopal",
    template: "%s · Visarjan Ghat Watch",
  },
  description:
    "Screening tool for Bhopal Municipal Corporation visarjan planning: ghat ranking against CPCB limits from MPPCB reports 2023–2025 (historical readings; recommendations need officer verification).",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${inter.variable} ${devanagari.variable} h-full`}>
      <body className="min-h-full">{children}</body>
    </html>
  );
}
