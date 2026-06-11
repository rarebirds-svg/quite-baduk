import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "com.inkbaduk.app",
  appName: "Inkbaduk",
  webDir: "out",
  plugins: {
    SplashScreen: {
      launchShowDuration: 600,
      backgroundColor: "#F5EFE6",
      showSpinner: false,
    },
  },
};

export default config;
