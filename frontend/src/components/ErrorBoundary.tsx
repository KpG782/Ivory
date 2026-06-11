"use client";

import { Component, type ReactNode } from "react";
import { IvoryLogo } from "./IvoryLogo";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

/**
 * Top-level error boundary. If a render throws anywhere in the app, the user
 * sees a calm branded recovery card instead of a blank white screen, and can
 * reload without losing the locally-stored session history.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: unknown): void {
    // Surface to the console for debugging; never crash the whole tree.
    console.error("Ivory UI error:", error);
  }

  private handleReload = (): void => {
    if (typeof window !== "undefined") {
      window.location.reload();
    }
  };

  render(): ReactNode {
    if (!this.state.hasError) {
      return this.props.children;
    }

    return (
      <main className="flex min-h-screen items-center justify-center px-4 py-8 text-[#191c1e]">
        <section
          role="alert"
          className="w-full max-w-md rounded-[2rem] border border-black/8 bg-white/85 p-8 text-center shadow-[0_20px_60px_rgba(15,23,42,0.08)] backdrop-blur"
        >
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full border border-[#d9c69b] bg-[#f8f3e6] p-2.5">
            <IvoryLogo className="h-full w-full" />
          </div>
          <h1 className="mt-4 font-[family-name:var(--font-display)] text-2xl font-bold tracking-[-0.03em] text-slate-950">
            Something went wrong
          </h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            The workspace hit an unexpected error. Your saved conversations are
            stored locally and are safe — reloading usually fixes this.
          </p>
          <button
            type="button"
            onClick={this.handleReload}
            className="ui-hover-lift mt-6 rounded-full bg-[#1f1f1f] px-5 py-3 text-sm font-semibold text-white transition hover:bg-black"
          >
            Reload workspace
          </button>
        </section>
      </main>
    );
  }
}
