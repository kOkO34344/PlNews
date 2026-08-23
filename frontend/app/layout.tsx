import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "3-3-3 Democracy-Aware News Analyst",
  description: "Daily digest with democracy and bias analysis.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="wrap">{children}</div>
      </body>
    </html>
  );
}
