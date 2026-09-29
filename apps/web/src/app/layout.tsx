import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SatQuery AI — Evidence-grounded Earth intelligence",
  description: "Query-driven Sentinel-1 and Sentinel-2 analysis powered by RS-InternVL.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
