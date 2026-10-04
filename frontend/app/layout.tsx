import type { Metadata } from "next";
import { Outfit } from "next/font/google";
import "./globals.css";

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-outfit",
  weight: ["300", "400", "500", "600", "700"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Quorum Verification Dashboard",
  description: "Decentralized reproducible build verification dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${outfit.variable} dark h-full`}>
      <body className="min-h-full font-sans antialiased bg-black text-white selection:bg-white selection:text-black">
        {children}
      </body>
    </html>
  );
}
