"use client";

import { useEffect, useRef } from "react";

interface DoumWidgetConfig {
  storeId: string;
  containerId: string;
  widgetScriptUrl: string;
  apiUrl?: string;
  productId?: string;
  userId?: string;
  theme?: string;
  position?: string;
  autoShow?: boolean;
  backgroundColor?: string;
  headerBackgroundColor?: string;
  inputBackgroundColor?: string;
  welcomeMessage?: string;
}

declare global {
  interface Window {
    Doum?: {
      init: (config: DoumWidgetConfig) => void;
    };
  }
}

interface DoumWidgetProps {
  productId: string;
  userId: string;
  containerId?: string;
  className?: string;
}

export default function DoumWidget({
  productId,
  userId,
  containerId = "doum-container",
  className,
}: DoumWidgetProps) {
  const isInitialized = useRef(false);

  useEffect(() => {
    if (isInitialized.current) {
      return;
    }

    const script = document.createElement("script");
    script.src = "https://doum-cdn.vercel.app/loader.min.js";
    script.async = true;

    script.onload = () => {
      if (window.Doum) {
        window.Doum.init({
          storeId: "1fcaa03d-16c9-49cd-940e-f53325d395ff",
          containerId,
          widgetScriptUrl: "https://doum-cdn.vercel.app/widget.min.js",
          userId,
          apiUrl: "wss://doum-chat.onrender.com",
          welcomeMessage: "Hi! Happy to help you find your next style!",
          productId,
        });
      }
    };

    document.head.appendChild(script);
    isInitialized.current = true;

    return () => {
      if (script.parentNode) {
        script.parentNode.removeChild(script);
      }
    };
  }, [containerId, productId, userId]);

  // Doum's loader mutates this element's attributes/children after mount,
  // which races React's hydration commit. Suppress the warning because we
  // explicitly *want* the client-side mutations to win.
  return <div id={containerId} className={className} suppressHydrationWarning />;
}
