import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from '@/components/theme-provider'
import { Toaster } from '@/components/ui/sonner'
import { Providers } from './providers'
import { EngineeringProvider } from '@/lib/engineeringContext'

const inter = Inter({
  subsets: ["latin"],
  display: 'swap',
  variable: "--font-inter",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  display: 'swap',
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "ECO-Draft 2D",
  description: "AI-powered mechanical part design tool with environmental impact analysis",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${inter.variable} ${jetbrainsMono.variable} font-sans antialiased`}
        suppressHydrationWarning
      >
        <Providers>
          <ThemeProvider
            attribute="class"
            defaultTheme="system"
            enableSystem
            disableTransitionOnChange
            storageKey="eco-draft-theme"
          >
            <EngineeringProvider>
              {children}
              <Toaster richColors position="top-right" />
            </EngineeringProvider>
          </ThemeProvider>
        </Providers>
      </body>
    </html>
  );
}
