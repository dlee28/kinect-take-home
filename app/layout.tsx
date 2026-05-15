import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Kinect — Personalized PDP",
  description: "A personalized H&M-style product detail page demo.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
