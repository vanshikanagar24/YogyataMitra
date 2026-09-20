const nextJest = require('next/jest');

const createJestConfig = nextJest({
  dir: './',
});

const customJestConfig = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testEnvironment: 'jest-environment-jsdom',
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/',
  },
  testMatch: ['<rootDir>/tests/unit/**/*.test.{ts,tsx}'],
};

module.exports = createJestConfig(customJestConfig);
