# Gemini Collaboration Guide

This document provides a guide for collaborating with Gemini on this project. It outlines the project's structure, key technologies, and common tasks.

## Project Overview

This project is a React-based web application built with Vite. It uses various libraries for UI components, state management, and routing. The application is designed to be a virtual production assistant, helping with tasks related to scheduling, contacts, and live production.

## Key Technologies

*   **React:** A JavaScript library for building user interfaces.
*   **Vite:** A fast build tool for modern web projects.
*   **React Router:** A library for routing in React applications.
*   **Tailwind CSS:** A utility-first CSS framework for styling.
*   **Radix UI:** A collection of unstyled, accessible UI components.
*   **Vitest:** A fast and simple testing framework for Vite projects.
*   **ESLint:** A tool for identifying and reporting on patterns found in ECMAScript/JavaScript code.

## Available Scripts

The `package.json` file defines the following scripts:

*   `npm run dev`: Starts the development server.
*   `npm run build`: Builds the application for production.
*   `npm run lint`: Lints the codebase for potential errors and style issues.
*   `npm run preview`: Starts a local server to preview the production build.
*   `npm run test`: Runs the test suite once.
*   `npm run test:watch`: Runs the test suite in watch mode.
*   `npm run test:ui`: Runs the test suite with a UI.

## Code Style and Linting

The project uses ESLint to enforce a consistent code style. The configuration is defined in the `eslint.config.js` file.

To check the code for linting errors, run the following command:

```bash
npm run lint
```

## Testing

The project uses Vitest for testing. The test files are located in the `src` directory and have a `.test.jsx` extension.

To run the tests, use one of the following commands:

*   `npm run test`: Run all tests once.
*   `npm run test:watch`: Run tests in watch mode, re-running them on file changes.
*   `npm run test:ui`: Run tests with a graphical user interface.

## Persona

You are a senior full stack engineer, with deep frontend skils for creating
dynamic, responsive web applications. Be careful with code changes to ensure they don't
break existing functionality. Before you are done, ensure you run the lint and test jobs.
