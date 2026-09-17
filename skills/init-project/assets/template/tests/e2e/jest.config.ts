import type { Config } from "jest";

const config: Config = {
  preset: "ts-jest",
  testEnvironment: "node",
  roots: ["<rootDir>"],
  testMatch: ["**/*.e2e.ts"],
  moduleNameMapper: {
    "^@helpers/(.*)$": "<rootDir>/helpers/$1",
  },
  setupFilesAfterEnv: ["<rootDir>/jest.setup.ts"],
  globalSetup: "<rootDir>/jest.global-setup.ts",
  testTimeout: 30_000,
  verbose: true,
  maxWorkers: 1,
  watchman: false,
};

export default config;
