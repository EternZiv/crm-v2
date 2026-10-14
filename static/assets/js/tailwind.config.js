window.tailwind.config = {
  theme: {
    colors: {
      white: '#FFFFFF',
      primary: {
        50: '#F8F8FD',
        100: '#F0F1FA',
        200: '#E6E8F7',
        300: '#D5D8F0',
        400: '#BCC1E5',
        500: '#9BA2D7',
        600: '#7C87C2',
        700: '#6873AE',
        800: '#515D98',
        900: '#38436F',
      },

      dark: {
        25:'#F0F0F0',
        50: '#E6E6E6',
        100: '#A8A8A8',
        200: '#515151',
        300: '#515151',
        400: '#64748B',
        500: '#190906',
        600: '#000000',
      },

      secondary: {
        50: '#f8fafc',
        100: '#f1f5f9',
        200: '#e2e8f0',
        300: '#cbd5e1',
        400: '#BCC1E5',
        500: '#9BA2D7',
        600: '#7C87C2',
        700: '#334155',
        800: '#1e293b',
        900: '#0f172a',
      },
      success: {
        light: "#86efac",
        DEFAULT: "#22c55e",
        dark: "#15803d",
      },
      warning: {
        light: "#fde68a",
        DEFAULT: "#f59e0b",
        dark: "#b45309",
      },
      danger: {
        light: "#fca5a5",
        DEFAULT: "#ef4444",
        dark: "#b91c1c",
      },
    },
    extend: {
      boxShadow: {
        card: "0px 0px 10px rgba(0, 0, 0, 0.05)",
      },
      spacing: {
        18: "4.5rem",
        72: "18rem",
        84: "21rem",
        96: "24rem",
      },
      borderRadius: {
        "4xl": "2rem",
        "5xl": "2.5rem",
      },
      fontSize: {
        xxs: "0.625rem",
      },
      height: {
        "screen-50": "50vh",
        "screen-75": "75vh",
      },
    },
  },
};
