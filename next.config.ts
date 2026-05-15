import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "**.hmstatic.net" },
      { protocol: "https", hostname: "**.h-cdn.com" },
      { protocol: "https", hostname: "image.hm.com" },
      { protocol: "https", hostname: "lp2.hm.com" },
      { protocol: "https", hostname: "huggingface.co" },
      { protocol: "https", hostname: "**.huggingface.co" },
      { protocol: "https", hostname: "qdrant-nextjs-demo-product-images.s3.us-east-1.amazonaws.com" },
      { protocol: "https", hostname: "*.amazonaws.com" },
    ],
  },
};

export default nextConfig;
