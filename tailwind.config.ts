import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        'brand-primary': '#181520',
        'brand-secondary': '#DEE7F1',
        'neutral-background': '#F8F7F7',
        'neutral-surface': '#FFFFFF',
        'text-primary': '#181520',
        'text-secondary': 'rgba(24, 21, 32, 0.7)',
        'text-onPrimary': '#FFFFFF',
      },
      fontFamily: {
        'primary': ['Bricolage Grotesque', 'sans-serif'],
        'secondary': ['Inter Tight', 'sans-serif'],
      },
      spacing: {
        's': '16px',
        'm': '24px',
        'l': '32px',
        'xl': '48px',
      },
      borderRadius: {
        'sm': '8px',
        'md': '16px',
        'lg': '40px',
        'full': '9999px',
      },
      fontSize: {
        'huge': 'clamp(3rem, 8vw, 7.5rem)',
      },
      animation: {
        "fade-in": "fadeIn 0.6s ease-out",
        "slide-up": "slideUp 0.6s ease-out",
        "slide-in-right": "slideInRight 0.6s ease-out",
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "float": "float 6s ease-in-out infinite",
        "gradient": "gradient 8s ease infinite",
        "shimmer": "shimmer 2s linear infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0", transform: "translateY(20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(30px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideInRight: {
          "0%": { opacity: "0", transform: "translateX(30px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-20px)" },
        },
        gradient: {
          "0%, 100%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
        },
        shimmer: {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(100%)" },
        },
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "gradient-conic": "conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))",
        "mesh-gradient": "linear-gradient(135deg, #667eea 0%, #764ba2 25%, #f093fb 50%, #feca57 75%, #48c9b0 100%)",
      },
    },
  },
  plugins: [],
}
};

export default config;
